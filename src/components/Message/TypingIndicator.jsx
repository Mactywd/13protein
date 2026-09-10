import { useEffect, useRef, useState } from "react";
import {
    initialTypingState,
    nextTypingState,
    visibleText,
    TYPE_MS,
} from "./typewriter";

// Self-contained cycling "thinking" indicator: types each variant in, holds,
// deletes, advances to the next (wrapping), forever. Owns its own timer so it
// never re-renders the parent messages array while cycling.
export default function TypingIndicator({ variants }) {
    const [state, setState] = useState(initialTypingState);
    const timerRef = useRef(null);

    useEffect(() => {
        if (!variants || variants.length === 0) return undefined;
        let current = initialTypingState();
        setState(current);
        function tick() {
            const { state: next, delay } = nextTypingState(current, variants);
            current = next;
            setState(next);
            timerRef.current = setTimeout(tick, delay);
        }
        timerRef.current = setTimeout(tick, TYPE_MS);
        return () => clearTimeout(timerRef.current);
    }, [variants]);

    const text = variants && variants.length ? visibleText(state, variants) : "";

    return (
        <div className="message ai typing-indicator" id="typing-indicator">
            <span>
                {text}
                <span className="typing-cursor" aria-hidden="true"></span>
            </span>
        </div>
    );
}
