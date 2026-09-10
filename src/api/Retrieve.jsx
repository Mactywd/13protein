import { createParser } from "eventsource-parser";

/**
 * Client per il backend 13 Protein (FastAPI + SSE).
 *
 * Talks to the Node server's /api/chat proxy, which forwards to the Python
 * backend's POST /chat. Native SSE events are translated here into the
 * eventHandlers contract that the Conversation/Message components already use,
 * so the UI layer stays unchanged.
 *
 * Native backend events (event name → data):
 *   text         { token }                       streamed AI text, one token per event
 *   buttons      { buttons: [{label, value}] }   clickable choices
 *   carousel     { cards: [{title, image, description, value}] }
 *   error        { message }
 *   lead_info    { info }                         final structured summary
 *   done         { step }                         end of this turn
 */
export default class Retrieve {
    constructor(eventHandlers, userId, isTesting = false) {
        this.isLeadInfoSet = false;
        this.apiBaseUrl = "/api";
        this.userId = userId; // used as backend session_id
        this.isTesting = isTesting;

        this.eventHandlers = eventHandlers || {
            messageHandlers: {
                onMessageStart: () => {},
                onMessageToken: () => {},
                onMessageEnd: () => {},
            },
            onChoice: () => {},
            onCarousel: () => {},
            onBegin: () => {},
            onResponseBegin: () => {},
            onResponseEnd: () => {},
            onConversationEnd: () => {},
            onLeadInfo: () => {},
            addTypingIndicator: () => {},
            removeTypingIndicator: () => {},
            setUserCanWrite: () => {},
        };
    }

    async sendStreamingRequest(message, defaultLanguage) {
        this.eventHandlers.onBegin();
        this.eventHandlers.addTypingIndicator(undefined);

        const dev = import.meta.env.MODE !== "production";
        if (dev) console.log("[Client] Chat request for session:", this.userId);

        const body = { session_id: this.userId, message: message ?? "" };
        if (defaultLanguage) body.default_language = defaultLanguage;
        if (this.isTesting) body.is_testing = true;

        const response = await fetch(`${this.apiBaseUrl}/chat`, {
            method: "POST",
            headers: {
                Accept: "text/event-stream",
                "Content-Type": "application/json",
            },
            body: JSON.stringify(body),
        });

        if (!response.ok || !response.body) {
            const errorText = await response.text();
            console.error("[Client] API failed:", response.status, errorText);
            this.eventHandlers.removeTypingIndicator();
            throw new Error(`API failed ${response.status} ${errorText}`);
        }

        // Streaming message accumulator state
        let messageOpen = false;

        const openMessage = () => {
            if (!messageOpen) {
                this.eventHandlers.removeTypingIndicator();
                this.eventHandlers.messageHandlers.onMessageStart();
                messageOpen = true;
            }
        };
        const closeMessage = () => {
            if (messageOpen) {
                this.eventHandlers.messageHandlers.onMessageEnd();
                messageOpen = false;
            }
        };
        const showStaticText = (text) => {
            closeMessage();
            this.eventHandlers.removeTypingIndicator();
            this.eventHandlers.messageHandlers.onMessageStart();
            this.eventHandlers.messageHandlers.onMessageToken(text);
            this.eventHandlers.messageHandlers.onMessageEnd();
        };

        const parser = createParser({
            onEvent: (event) => {
                const name = event.event;
                if (!name) return;

                let data = {};
                if (event.data) {
                    try {
                        data = JSON.parse(event.data);
                    } catch {
                        throw new Error("Failed to parse event data: " + event.data);
                    }
                }

                switch (name) {
                    case "text":
                        openMessage();
                        this.eventHandlers.messageHandlers.onMessageToken(data.token || "");
                        break;

                    case "buttons": {
                        closeMessage();
                        this.eventHandlers.removeTypingIndicator();
                        const buttons = (data.buttons || []).map((b) => ({
                            name: b.label,
                            request: { type: "text", payload: { label: b.value, name: b.label } },
                        }));
                        this.eventHandlers.onChoice({
                            type: "choice",
                            payload: { buttons },
                        });
                        break;
                    }

                    case "carousel": {
                        closeMessage();
                        this.eventHandlers.removeTypingIndicator();
                        const cards = (data.cards || []).map((c) => ({
                            title: c.title,
                            imageUrl: c.image,
                            description: { text: c.description },
                            buttons: [{ name: c.value, label: c.title }],
                        }));
                        this.eventHandlers.onCarousel({
                            type: "carousel",
                            payload: { cards },
                        });
                        break;
                    }

                    case "message_break":
                        // Mid-turn separator: close the current bubble so the
                        // following text tokens open a fresh one, and re-show the
                        // thinking indicator to bridge the gap while the backend
                        // works on the next bubble (the next text/buttons/carousel
                        // removes it again).
                        closeMessage();
                        this.eventHandlers.addTypingIndicator(undefined);
                        break;

                    case "error":
                        showStaticText(data.message || "Something went wrong.");
                        break;

                    case "lead_info":
                        if (!this.isLeadInfoSet) {
                            this.eventHandlers.onLeadInfo(data.info);
                            this.isLeadInfoSet = true;
                        }
                        break;

                    case "done":
                        closeMessage();
                        this.eventHandlers.removeTypingIndicator();
                        this.eventHandlers.onResponseEnd();
                        // Respect the backend's per-step input gating (button-only
                        // steps send input_enabled:false). Default true keeps
                        // backward compatibility with any event missing the field.
                        this.eventHandlers.setUserCanWrite(data.input_enabled !== false);
                        if (data.step === "completed") {
                            this.eventHandlers.onConversationEnd();
                        }
                        break;

                    default:
                        if (dev) console.warn("[Client] Unknown event:", name, data);
                }
            },
        });

        return new Promise((resolve, reject) => {
            (async () => {
                try {
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) {
                            closeMessage();
                            resolve();
                            break;
                        }
                        parser.feed(decoder.decode(value, { stream: true }));
                    }
                } catch (error) {
                    console.error("[Client] Stream error:", error);
                    closeMessage();
                    reject(error);
                }
            })();
        });
    }

    async conversationInit(language = "en") {
        // Pass the language code ("it"/"en") to the backend on the first turn.
        return this.sendStreamingRequest("", language);
    }

    async sendTextRequest(text) {
        return this.sendStreamingRequest(text);
    }

    async sendClickRequest(request) {
        // Button/carousel clicks resolve to a plain message value upstream;
        // kept for API compatibility.
        const text =
            typeof request === "string"
                ? request
                : request?.payload?.label ?? request?.payload ?? "";
        return this.sendStreamingRequest(text);
    }
}
