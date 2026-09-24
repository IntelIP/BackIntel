#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { isAbsolute, relative, resolve } from 'node:path';

const allowedTypes = new Set(['static', 'schema', 'semantic', 'workflow', 'visual', 'operational', 'security']);

function parseArgs(argv) {
  const values = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    if (!['--manifest', '--check'].includes(key) || !argv[i + 1]) {
      throw new Error(`Invalid argument: ${key}`);
    }
    values[key] = argv[i + 1];
  }
  if (!values['--manifest'] || !['schema', 'policy'].includes(values['--check'])) {
    throw new Error('Usage: check-contract.mjs --manifest PATH --check schema|policy');
  }
  return values;
}

function checkSchema(manifest) {
  const issues = [];
  const acceptance = manifest?.acceptance;
  const validators = manifest?.validators;
  if (manifest?.$schema !== 'tabellio-validation/v0.2') issues.push('Unsupported or missing $schema');
  for (const key of ['id', 'source', 'risk']) {
    if (typeof acceptance?.[key] !== 'string' || !acceptance[key].trim()) issues.push(`acceptance.${key} must be a non-empty string`);
  }
  if (!['low', 'medium', 'high', 'critical'].includes(acceptance?.risk)) issues.push('acceptance.risk must be low, medium, high, or critical');
  for (const key of ['outcomes', 'invariants', 'forbiddenOutcomes', 'requiredValidatorTypes']) {
    if (!Array.isArray(acceptance?.[key]) || acceptance[key].length === 0 || acceptance[key].some((value) => typeof value !== 'string' || !value.trim())) {
      issues.push(`acceptance.${key} must be a non-empty string array`);
    }
  }
  if (Array.isArray(acceptance?.requiredValidatorTypes)) {
    for (const type of acceptance.requiredValidatorTypes) if (!allowedTypes.has(type)) issues.push(`Unknown required validator type: ${type}`);
  }
  if (!Array.isArray(validators) || validators.length === 0) issues.push('validators must be a non-empty array');
  const ids = new Set();
  for (const [index, validator] of (Array.isArray(validators) ? validators : []).entries()) {
    const at = `validators[${index}]`;
    if (typeof validator?.id !== 'string' || !validator.id.trim() || ids.has(validator.id)) issues.push(`${at}.id must be non-empty and unique`);
    else ids.add(validator.id);
    if (!allowedTypes.has(validator?.type)) issues.push(`${at}.type is invalid`);
    if (!Array.isArray(validator?.argv) || validator.argv.length === 0 || validator.argv.some((arg) => typeof arg !== 'string')) issues.push(`${at}.argv must be a non-empty string array (no shell command)`);
    if (typeof validator?.cwd !== 'string' || isAbsolute(validator.cwd) || relative(process.cwd(), resolve(process.cwd(), validator.cwd)).startsWith('..')) issues.push(`${at}.cwd must stay inside the repository`);
    const executable = typeof validator?.argv?.[0] === 'string' ? validator.argv[0] : '';
    if (['sh', 'bash', 'zsh', 'cmd', 'powershell', 'pwsh'].includes(executable.split('/').at(-1).toLowerCase())) issues.push(`${at}.argv must invoke a program directly, not a shell`);
    if (!Number.isInteger(validator?.timeout) || validator.timeout < 1) issues.push(`${at}.timeout must be a positive integer`);
    if (typeof validator?.required !== 'boolean') issues.push(`${at}.required must be boolean`);
    if (typeof validator?.evidencePath !== 'string' || !validator.evidencePath.trim() || isAbsolute(validator.evidencePath) || relative('.', resolve('.', validator.evidencePath)).startsWith('..')) issues.push(`${at}.evidencePath must stay inside its output directory`);
    if (!validator?.metricThresholds || typeof validator.metricThresholds !== 'object' || Array.isArray(validator.metricThresholds)) issues.push(`${at}.metricThresholds must be an object`);
    if (typeof validator?.costPolicy?.requiredTelemetry !== 'boolean' || !Number.isFinite(validator?.costPolicy?.maxUsd) || validator.costPolicy.maxUsd < 0) issues.push(`${at}.costPolicy requires requiredTelemetry and non-negative maxUsd`);
  }
  for (const type of acceptance?.requiredValidatorTypes ?? []) {
    if (!validators?.some((validator) => validator.type === type && validator.required === true)) issues.push(`Missing required validator of type ${type}`);
  }
  return issues;
}

function checkPolicy(manifest) {
  const issues = [];
  const text = [...manifest.acceptance.outcomes, ...manifest.acceptance.invariants, ...manifest.acceptance.forbiddenOutcomes].join('\n').toLowerCase();
  for (const term of ['data', 'jev', 'prediction', 'model', 'ui', 'cost', 'recovery', 'security']) {
    if (!text.includes(term)) issues.push(`Acceptance contract does not mention ${term} validation`);
  }
  if (!text.includes('blocked')) issues.push('Contract must define blocked handling for missing evidence');
  if (!manifest.acceptance.requiredValidatorTypes.includes('static') || !manifest.acceptance.requiredValidatorTypes.includes('schema')) {
    issues.push('Bootstrap must require static and schema validation');
  }
  if (manifest.validators.some((validator) => validator.costPolicy.maxUsd !== 0)) issues.push('Bootstrap validators must have a zero-USD cap');
  return issues;
}

try {
  const args = parseArgs(process.argv.slice(2));
  const manifest = JSON.parse(readFileSync(args['--manifest'], 'utf8'));
  const issues = checkSchema(manifest);
  if (args['--check'] === 'policy' && issues.length === 0) issues.push(...checkPolicy(manifest));
  if (issues.length) {
    console.error(JSON.stringify({ status: 'failed', check: args['--check'], issues }, null, 2));
    process.exitCode = 1;
  } else {
    console.log(JSON.stringify({ status: 'passed', check: args['--check'], summary: `Manifest ${args['--check']} check passed.` }));
  }
} catch (error) {
  console.error(JSON.stringify({ status: 'failed', summary: error.message }));
  process.exitCode = 1;
}
