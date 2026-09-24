#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

export function overallStatus(validatorResults, blockers = []) {
  if (validatorResults.some((result) => result.status === 'failed')) return 'failed';
  if (blockers.length || validatorResults.some((result) => result.status === 'blocked')) return 'blocked';
  return 'passed';
}

function argsOf(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    if (!['--manifest', '--expected-commit', '--output'].includes(key) || !argv[index + 1]) throw new Error(`Invalid argument: ${key}`);
    args[key] = argv[index + 1];
  }
  if (!args['--manifest'] || !args['--expected-commit'] || !args['--output']) {
    throw new Error('Usage: run.mjs --manifest PATH --expected-commit SHA --output DIR');
  }
  return args;
}

function git(args, cwd) {
  const result = spawnSync('git', args, { cwd, encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || `git ${args.join(' ')} failed`);
  return result.stdout.trim();
}

function hash(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function writeJson(path, value) {
  const bytes = Buffer.from(`${JSON.stringify(value, null, 2)}\n`);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, bytes);
  return { sha256: hash(bytes), bytes: bytes.length };
}

function run(root, args) {
  const manifestPath = resolve(root, args['--manifest']);
  const outputDir = resolve(root, args['--output']);
  if (relative(root, manifestPath).startsWith('..') || isAbsolute(relative(root, manifestPath))) throw new Error('Manifest path must stay inside the repository.');
  if (relative(root, outputDir).startsWith('..') || isAbsolute(relative(root, outputDir)) || relative(root, outputDir) === '.') throw new Error('Output directory must be a dedicated path inside the repository.');
  const expectedCommit = args['--expected-commit'];
  const startedAt = new Date().toISOString();
  const blockers = [];
  const results = [];
  let manifest;

  try {
    manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  } catch (error) {
    blockers.push(`Cannot load validation manifest: ${error.message}`);
    manifest = { acceptance: { id: 'unknown' }, validators: [] };
  }

  let actualCommit = null;
  try {
    actualCommit = git(['rev-parse', 'HEAD'], root);
    if (!/^[a-f0-9]{40}$/i.test(expectedCommit) || actualCommit !== expectedCommit) {
      blockers.push(`Expected commit ${expectedCommit} does not match checked-out HEAD ${actualCommit}.`);
    }
    const status = git(['status', '--porcelain', '--untracked-files=all'], root);
    const outputRelative = `${relative(root, outputDir).replaceAll('\\', '/')}/`;
    const relevantChanges = status.split('\n').filter(Boolean).filter((line) => {
      const path = line.slice(3).trim().replaceAll('\\', '/');
      return path !== outputRelative.slice(0, -1) && !path.startsWith(outputRelative);
    });
    if (relevantChanges.length) blockers.push('Working tree has uncommitted changes; exact-candidate validation is blocked.');
  } catch (error) {
    blockers.push(`Cannot establish Git candidate identity: ${error.message}`);
  }

  if (!Array.isArray(manifest.validators) || manifest.validators.length === 0) {
    blockers.push('Manifest has no validators to execute.');
  } else {
    for (const validator of manifest.validators) {
      if (!validator || !Array.isArray(validator.argv) || validator.argv.length === 0 || validator.argv.some((arg) => typeof arg !== 'string') || typeof validator.id !== 'string' || typeof validator.evidencePath !== 'string' || !Number.isInteger(validator.timeout) || validator.timeout < 1) {
        results.push({ validatorId: validator?.id ?? 'invalid-validator', status: 'failed', summary: 'Validator entry is malformed.', metrics: {}, costTelemetry: { state: 'blocked', usd: null, modelCalls: null, toolCalls: null }, artifacts: [] });
        continue;
      }
      const validatorCwd = resolve(root, validator.cwd || '.');
      const cwdRelative = relative(root, validatorCwd);
      const evidencePath = resolve(outputDir, validator.evidencePath);
      const evidenceRelative = relative(outputDir, evidencePath);
      const executable = validator.argv[0];
      if (isAbsolute(validator.cwd || '') || cwdRelative.startsWith('..') || isAbsolute(validator.evidencePath) || evidenceRelative.startsWith('..') || ['sh', 'bash', 'zsh', 'cmd', 'powershell', 'pwsh'].includes(executable.split('/').at(-1).toLowerCase())) {
        results.push({ validatorId: validator.id, status: 'failed', summary: 'Validator command or paths violate the repository boundary.', metrics: {}, costTelemetry: { state: 'blocked', usd: null, modelCalls: null, toolCalls: null }, artifacts: [] });
        continue;
      }
      const began = Date.now();
      const processResult = spawnSync(validator.argv[0], validator.argv.slice(1), {
        cwd: validatorCwd,
        encoding: 'utf8',
        timeout: Math.max(1, validator.timeout) * 1000,
        shell: false,
        env: { ...process.env, TABELLIO_EXPECTED_COMMIT: expectedCommit },
      });
      const durationMs = Date.now() - began;
      const stdoutPath = resolve(outputDir, `${validator.id}.stdout.txt`);
      const stderrPath = resolve(outputDir, `${validator.id}.stderr.txt`);
      const stdout = processResult.stdout ?? '';
      const stderr = processResult.stderr ?? processResult.error?.message ?? '';
      const stdoutArtifact = writeJsonText(stdoutPath, stdout, relative(root, stdoutPath).replaceAll('\\\\', '/'));
      const stderrArtifact = writeJsonText(stderrPath, stderr, relative(root, stderrPath).replaceAll('\\\\', '/'));
      const status = processResult.error
        ? 'blocked'
        : processResult.status === 0 ? 'passed' : 'failed';
      const summary = status === 'passed'
        ? `Validator ${validator.id} exited successfully.`
        : status === 'blocked'
          ? `Validator ${validator.id} could not run: ${processResult.error.message}`
          : `Validator ${validator.id} failed (exit ${processResult.status}).`;
      const result = {
        validatorId: validator.id,
        status,
        summary,
        metrics: { duration_ms: durationMs, exit_code: processResult.status ?? -1 },
        costTelemetry: { state: 'measured', usd: 0, modelCalls: 0, toolCalls: 0 },
        artifacts: [stdoutArtifact, stderrArtifact],
      };
      writeJson(evidencePath, { schema: 'tabellio-validator-evidence/v0.1', ...result, candidateCommit: actualCommit });
      results.push(result);
    }
  }

  const status = overallStatus(results, blockers);
  const finishedAt = new Date().toISOString();
  const report = {
    schema: 'tabellio-validation-result/v0.3',
    acceptanceId: manifest.acceptance?.id ?? 'unknown',
    status,
    expectedCommit,
    actualCommit,
    startedAt,
    finishedAt,
    blockers,
    validators: results,
  };
  const reportPath = resolve(outputDir, 'run-report.json');
  const reportArtifact = writeJson(reportPath, report);
  const manifestBytes = (() => { try { return readFileSync(manifestPath); } catch { return Buffer.alloc(0); } })();
  const evidence = {
    schema: 'tabellio-validation-result/v0.3',
    acceptanceId: report.acceptanceId,
    status,
    candidateCommit: actualCommit,
    expectedCommit,
    summary: blockers.join(' ') || `Ran ${results.length} validator(s); final status: ${status}.`,
    validators: results,
    costTelemetry: { state: 'measured', usd: 0, modelCalls: 0, toolCalls: 0 },
    artifacts: [
      { name: 'run-report.json', uri: relative(root, reportPath).replaceAll('\\', '/'), sha256: reportArtifact.sha256, mediaType: 'application/json', bytes: reportArtifact.bytes },
      { name: 'tabellio.validation.json', uri: relative(root, manifestPath).replaceAll('\\', '/'), sha256: hash(manifestBytes), mediaType: 'application/json', bytes: manifestBytes.length },
    ],
  };
  writeJson(resolve(outputDir, 'evidence.json'), evidence);
  return status;
}

function writeJsonText(path, text, uri) {
  const bytes = Buffer.from(text);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, bytes);
  return { name: path.split('/').at(-1), uri, sha256: hash(bytes), mediaType: 'text/plain', bytes: bytes.length };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const status = run(process.cwd(), argsOf(process.argv.slice(2)));
    console.log(`Tabellio validation status: ${status}`);
    process.exitCode = status === 'passed' ? 0 : status === 'failed' ? 1 : 2;
  } catch (error) {
    console.error(error.message);
    process.exitCode = 2;
  }
}
