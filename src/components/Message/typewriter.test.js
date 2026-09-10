import { describe, it, expect } from "vitest";
import {
    initialTypingState,
    nextTypingState,
    visibleText,
    TYPE_MS,
    DELETE_MS,
    HOLD_FULL_MS,
    HOLD_EMPTY_MS,
} from "./typewriter";

const VARIANTS = ["ab", "cd"];

describe("typewriter engine", () => {
    it("starts empty on the first variant, typing", () => {
        const s = initialTypingState();
        expect(s).toEqual({ index: 0, chars: 0, phase: "typing" });
        expect(visibleText(s, VARIANTS)).toBe("");
    });

    it("reveals one character per tick while typing", () => {
        let r = nextTypingState(initialTypingState(), VARIANTS);
        expect(r.delay).toBe(TYPE_MS);
        expect(r.state).toEqual({ index: 0, chars: 1, phase: "typing" });
        expect(visibleText(r.state, VARIANTS)).toBe("a");

        r = nextTypingState(r.state, VARIANTS);
        expect(r.state).toEqual({ index: 0, chars: 2, phase: "typing" });
        expect(visibleText(r.state, VARIANTS)).toBe("ab");
    });

    it("holds the full word, then switches to deleting", () => {
        const r = nextTypingState({ index: 0, chars: 2, phase: "typing" }, VARIANTS);
        expect(r.delay).toBe(HOLD_FULL_MS);
        expect(r.state).toEqual({ index: 0, chars: 2, phase: "deleting" });
        expect(visibleText(r.state, VARIANTS)).toBe("ab"); // full word visible during hold
    });

    it("removes one character per tick while deleting", () => {
        const r = nextTypingState({ index: 0, chars: 2, phase: "deleting" }, VARIANTS);
        expect(r.delay).toBe(DELETE_MS);
        expect(r.state).toEqual({ index: 0, chars: 1, phase: "deleting" });
        expect(visibleText(r.state, VARIANTS)).toBe("a");
    });

    it("advances to the next variant once emptied, after a pause", () => {
        const r = nextTypingState({ index: 0, chars: 0, phase: "deleting" }, VARIANTS);
        expect(r.delay).toBe(HOLD_EMPTY_MS);
        expect(r.state).toEqual({ index: 1, chars: 0, phase: "typing" });
        expect(visibleText(r.state, VARIANTS)).toBe("");
    });

    it("wraps from the last variant back to the first", () => {
        const r = nextTypingState({ index: 1, chars: 0, phase: "deleting" }, VARIANTS);
        expect(r.state.index).toBe(0);
        expect(r.state.phase).toBe("typing");
    });
});
