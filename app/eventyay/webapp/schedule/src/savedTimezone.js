import moment from 'moment-timezone'

/**
 * Pick the timezone to show from the value saved by the timezone picker.
 * Any timezone moment-timezone knows is kept, including ones chosen under
 * "Other Timezones"; a missing or unknown value falls back to the event timezone.
 */
export function resolveSavedTimezone (saved, fallback) {
	return saved && moment.tz.zone(saved) ? saved : fallback
}
