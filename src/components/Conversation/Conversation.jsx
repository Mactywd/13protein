import Chat from "../Chat/Chat";
import UserInput from "../UserInput/UserInput";
import Retrieve from "../../api/Retrieve";

import ConversationContext from "../../contexts/ConversationContext";
import { useLanguage } from "../../contexts/LanguageContext";
import { trackEvent } from "../../utils/track.js";
import { useState, useEffect, useRef } from "react";
import { authFetch } from "../../admin/auth";

import "./Conversation.css";

export default function Conversation({ endChat, updateLeadInfo, testingMode = false }) {
	const { language, t, localePath } = useLanguage();
	const [aiTyping, setAiTyping] = useState(false);
	const [aiTypingUpdates, setAiTypingUpdates] = useState(0);
	const [userCanWrite, setUserCanWrite] = useState(false);
	const textareaRef = useRef(null);
	const hasInitialized = useRef(false);

	// Generate a fresh backend session id per conversation
	const initial = (import.meta.env.MODE || "dev").charAt(0).toUpperCase();

	const userId = initial + "_" + Math.random().toString(36).substring(2, 9) + "_" + Date.now();
	const userIdRef = useRef(userId);

	const messageRefs = useRef([]); // holds DOM nodes for each message
	const containerRef = useRef(null); // scroll container
	const spacerRef = useRef(null); // bottom slack
	const streamingMessageRef = useRef(null); // accumulates tokens during streaming
	const animationFrameRef = useRef(null); // for batching UI updates

	// Messages state
	const [showReloadModal, setShowReloadModal] = useState(false);
	const [showSkipModal, setShowSkipModal] = useState(false);

	// Messages state
	const [messages, setMessages] = useState([]);
	function addMessage(data) {
		setMessages((messages) => [...messages, data]);
	}
	function addMessageToken(newToken) {
		// Accumulate token in ref to prevent race conditions
		if (streamingMessageRef.current !== null) {
			streamingMessageRef.current += newToken;

			// Schedule a UI update (batched with requestAnimationFrame)
			if (!animationFrameRef.current) {
				animationFrameRef.current = requestAnimationFrame(() => {
					animationFrameRef.current = null;
					const currentContent = streamingMessageRef.current;

					setMessages((messages) => {
						if (messages.length === 0) return messages;

						const lastMessage = {
							...messages[messages.length - 1],
							payload: { message: currentContent },
						};

						return [...messages.slice(0, -1), lastMessage];
					});
				});
			}
		}
	}
	function addTrace(trace, sender) {
		trace.sender = sender;
		trace.additionalClasses = [];
		addMessage(trace);
	}

	function updateAiTyping() {
		setAiTypingUpdates((prev) => prev + 1);
	}

	// AI RESPONSE HANDLERS
	const eventHandlers = {
		messageHandlers: {
			onMessageStart: () => {
				streamingMessageRef.current = ""; // Initialize streaming accumulator
				addMessage({
					sender: "ai",
					type: "text",
					payload: { message: "" },
				});
			},
			onMessageToken: (token) => addMessageToken(token),
			onMessageEnd: () => {
				// Flush any pending animation frame
				if (animationFrameRef.current) {
					cancelAnimationFrame(animationFrameRef.current);
					animationFrameRef.current = null;

					// Apply final state
					const finalContent = streamingMessageRef.current;
					setMessages((messages) => {
						if (messages.length === 0) return messages;

						const lastMessage = {
							...messages[messages.length - 1],
							payload: { message: finalContent },
						};

						return [...messages.slice(0, -1), lastMessage];
					});
				}
				streamingMessageRef.current = null; // Clear the accumulator
			},
		},
		onChoice: (payload) => addTrace(payload, "ai"),
		onCarousel: (payload) => addTrace(payload, "ai"),
		onBegin: () => {},
		addTypingIndicator: (message) => renderTyping(message),
		removeTypingIndicator: () => renderTyping(null),
		onResponseBegin: () => {},
		onResponseEnd: () => {
			// AI finished → collapse spacer
			if (spacerRef.current) {
				spacerRef.current.style.height = "0px";
			}
		},
		onConversationEnd: () => { trackEvent('chat_complete', language); endChat(userIdRef.current); },
		onLeadInfo: (leadInfo) => updateLeadInfo(leadInfo),
		setUserCanWrite: (canWrite) => setUserCanWrite(canWrite),
	};

	const retrieve = new Retrieve(eventHandlers, userIdRef.current, testingMode);

	// Cleanup animation frame on unmount
	useEffect(() => {
		return () => {
			if (animationFrameRef.current) {
				cancelAnimationFrame(animationFrameRef.current);
			}
		};
	}, []);

	// Show a static error bubble and clear the typing indicator. Used when a
	// turn fails (network drop, backend down) so the user is never left staring
	// at a silent, frozen chat.
	function showTurnError(text, reenableInput) {
		renderTyping(null);
		streamingMessageRef.current = null;
		addMessage({ sender: "ai", type: "text", payload: { message: text } });
		if (reenableInput) setUserCanWrite(true);
	}

	// Fetch initial AI message
	useEffect(function () {
		async function conversationInit() {
			if (hasInitialized.current) {
				return;
			}
			hasInitialized.current = true;
			try {
				await retrieve.conversationInit(language);
			} catch (err) {
				console.error("[Conversation] init failed:", err);
				showTurnError(t.chat.initError, false);
			}
		}
		setTimeout(() => {
			conversationInit();
		}, 30);
	});

	// AI typing indicator
	useEffect(
		function () {
			if (aiTyping) {
				setMessages((messages) =>
					messages.filter((msg) => msg.type !== "typing")
				);
				addMessage({
					sender: "ai",
					type: "typing",
					payload: { variants: t.chat.typingVariants },
				});
			} else {
				setMessages((messages) =>
					messages.filter((msg) => msg.type !== "typing")
				);

				const isTouchDevice =
					"ontouchstart" in window || navigator.maxTouchPoints > 0;

				setTimeout(() => {
					if (!isTouchDevice && textareaRef.current) {
						textareaRef.current.focus();
					}
				}, 100);
			}
		},
		// eslint-disable-next-line react-hooks/exhaustive-deps
		[aiTypingUpdates]
	);

	// Scroll + expand spacer on user messages
	useEffect(() => {
		const last = messages[messages.length - 1];
		if (!last || last.sender !== "user") return; // only for user messages

		const container = containerRef.current;
		const lastMessageEl = messageRefs.current[messages.length - 1];

		if (spacerRef.current) {
			spacerRef.current.style.height = "200px";
		}

		if (container && lastMessageEl) {
			// align user message at the top
			lastMessageEl.scrollIntoView({
				block: "start",
				behavior: "smooth",
			});
		}
	}, [messages]);

	// AI typing renderer
	function renderTyping(message) {
		setAiTyping(message !== null);
		updateAiTyping();
	}

	// User actions
	async function handleMessageSend(message) {
		addMessage(message);
		// Button/carousel clicks carry a separate sendValue (backend value);
		// typed messages send their text directly.
		try {
			await retrieve.sendTextRequest(message.payload.sendValue ?? message.payload.message);
		} catch (err) {
			// The turn failed mid-flight (network blip, proxy timeout). The
			// backend persists a turn only on success, so re-sending is safe;
			// re-enable the input so the user can actually retry.
			console.error("[Conversation] send failed:", err);
			showTurnError(t.chat.sendError, true);
		}
	}

	function handleEnd() {
		endChat();
	}

	function confirmReload() {
		sessionStorage.setItem("agent13_skipLanding", "1");
		window.location.reload();
	}

	async function confirmSkip() {
		setShowSkipModal(false);
		const res = await authFetch("/api/chat/skip", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ session_id: userIdRef.current }),
		});
		if (!res.ok) return;
		const data = await res.json();
		eventHandlers.onLeadInfo(data.lead_info);
		eventHandlers.onConversationEnd();
	}

	// Render
	return (
		<ConversationContext.Provider
			value={{ handleMessageSend, handleEnd }}
		>
			<section className="chat-section" id="chat-section">
				<div className="container">
					<div className="chat-header">
						<h2 className="section-title">{t.chat.title}</h2>
					</div>
					<div
						className="chat-container card"
						id="chat-container"
						ref={containerRef}
					>
						<button
							type="button"
							className="reload-button"
							aria-label={t.chat.reloadTooltip}
							title={t.chat.reloadTooltip}
							onClick={() => setShowReloadModal(true)}
						>
							↻
						</button>
						{testingMode && (
							<button
								type="button"
								className="skip-button"
								aria-label={t.chat.skipTooltip}
								title={t.chat.skipTooltip}
								onClick={() => setShowSkipModal(true)}
							>
								⏭
							</button>
						)}
						<Chat
							messages={messages}
							messageRefs={messageRefs}
							chatBottomRef={spacerRef}
							setUserCanWrite={setUserCanWrite}
						/>
						<UserInput
							onSendMessage={handleMessageSend}
							userCanWrite={userCanWrite}
							setUserCanWrite={setUserCanWrite}
							textareaRef={textareaRef}
						/>
					</div>
					{/* AI Act art. 50.1 + rinvio all'informativa, sotto la barra di input.
					    Deve restare QUI (schermata di chat) e non solo sulla landing:
					    il pulsante ↻ rientra in conversazione saltando la landing via
					    il flag sessionStorage agent13_skipLanding. */}
					<p className="chat-ai-disclosure">
						{t.chat.aiDisclosure}{" "}
						<a href={localePath("/privacy-policy")} target="_blank" rel="noopener noreferrer">
							{t.chat.aiDisclosureLink}
						</a>
					</p>
				</div>
			{showReloadModal && (
				<div className="reload-modal-overlay" onClick={() => setShowReloadModal(false)}>
					<div className="reload-modal" onClick={(e) => e.stopPropagation()}>
						<p>{t.chat.reloadConfirm}</p>
						<div className="reload-modal-actions">
							<button type="button" className="reload-modal-cancel" onClick={() => setShowReloadModal(false)}>
								{t.chat.reloadNo}
							</button>
							<button type="button" className="reload-modal-confirm" onClick={confirmReload}>
								{t.chat.reloadYes}
							</button>
						</div>
					</div>
				</div>
			)}
			{showSkipModal && (
				<div className="reload-modal-overlay" onClick={() => setShowSkipModal(false)}>
					<div className="reload-modal" onClick={(e) => e.stopPropagation()}>
						<p>{t.chat.skipConfirm}</p>
						<div className="reload-modal-actions">
							<button type="button" className="reload-modal-cancel" onClick={() => setShowSkipModal(false)}>
								{t.chat.skipNo}
							</button>
							<button type="button" className="reload-modal-confirm" onClick={confirmSkip}>
								{t.chat.skipYes}
							</button>
						</div>
					</div>
				</div>
			)}
			</section>
		</ConversationContext.Provider>
	);
}
