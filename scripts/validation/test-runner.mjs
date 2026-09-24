#!/usr/bin/env node
import assert from 'node:assert/strict';
import { overallStatus } from './run.mjs';

assert.equal(overallStatus([{ status: 'passed' }]), 'passed');
assert.equal(overallStatus([{ status: 'failed' }]), 'failed');
assert.equal(overallStatus([{ status: 'passed' }], ['candidate is dirty']), 'blocked');
assert.equal(overallStatus([{ status: 'blocked' }]), 'blocked');
assert.equal(overallStatus([{ status: 'failed' }], ['candidate is dirty']), 'failed');
console.log('Validation status self-tests passed (passed, failed, blocked, precedence).');
