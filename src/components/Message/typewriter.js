// Pure phase-machine for the "thinking" typewriter indicator.
// No React / DOM here, so it is unit-testable in the default (node) vitest env.
// TypingIndicator.jsx drives it with setTimeout.

export const TYPE_MS = 45;        // per-character reveal while typing
export const DELETE_MS = 25;      // per-character removal while deleting
export const HOLD_FULL_MS = 1200; // pause once a variant is fully typed
export const HOLD_EMPTY_MS = 300; // pause on an empty line before the next variant

// state: { index: number, chars: number, phase: "typing" | "deleting" }
export function initialTypingState() {
    return { index: 0, chars: 0, phase: "typing" };
}

// Compute the next state and how long to wait before the following tick.
// Returns { state, delay }.
export function nextTypingState(state, variants) {
    const word = variants[state.index] ?? "";

    if (state.phase === "typing") {
        if (state.chars < word.length) {
            return { state: { ...state, chars: state.chars + 1 }, delay: TYPE_MS };
        }
        // Fully typed: hold the complete word, then start deleting.
        return { state: { ...state, phase: "deleting" }, delay: HOLD_FULL_MS };
    }

    // deleting
    if (state.chars > 0) {
        return { state: { ...state, chars: state.chars - 1 }, delay: DELETE_MS };
    }
    // Emptied: advance to the next variant (wrapping) and resume typing.
    const index = (state.index + 1) % variants.length;
    return { state: { index, chars: 0, phase: "typing" }, delay: HOLD_EMPTY_MS };
}

// Substring currently visible for the given state.
export function visibleText(state, variants) {
    const word = variants[state.index] ?? "";
    return word.slice(0, state.chars);
}
