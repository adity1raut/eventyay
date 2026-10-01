/**
 * Checks for restoring the timezone saved by the schedule's timezone picker.
 * Run: node --test src/savedTimezone.test.js
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveSavedTimezone } from './savedTimezone.js'

test('keeps a saved timezone from the Other Timezones list', () => {
	assert.equal(resolveSavedTimezone('Asia/Tokyo', 'Europe/Berlin'), 'Asia/Tokyo')
})

test('keeps the saved event timezone', () => {
	assert.equal(resolveSavedTimezone('Europe/Berlin', 'Europe/Berlin'), 'Europe/Berlin')
})

test('falls back to the event timezone when nothing is saved', () => {
	assert.equal(resolveSavedTimezone(null, 'Europe/Berlin'), 'Europe/Berlin')
	assert.equal(resolveSavedTimezone('', 'Europe/Berlin'), 'Europe/Berlin')
})

test('falls back to the event timezone for an unknown value', () => {
	assert.equal(resolveSavedTimezone('Mars/Olympus_Mons', 'Europe/Berlin'), 'Europe/Berlin')
	assert.equal(resolveSavedTimezone('undefined', 'Europe/Berlin'), 'Europe/Berlin')
})
