import { useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import './UserInput.css';

export default function UserInput({onSendMessage, userCanWrite, setUserCanWrite, textareaRef}) {
	const { t } = useLanguage();
	const [messageContent, setMessageContent] = useState ('');

	function handleChange (e) {
		setMessageContent (e.target.value);
	}

	function handleKeyDown(e) {
		if (e.key === "Enter" &&
			!e.shiftKey &&
			!e.ctrlKey &&
			!e.altKey
		) {
			handleSubmit(e)
		}
	}

	function handleSubmit (e) {
		e.preventDefault ();
		if (messageContent.trim ()) {
			setMessageContent ('');

			onSendMessage({
				sender: 'user',
				type: 'text',
				payload: {
					message: messageContent,
				},
			});

			setUserCanWrite(false);
		}
	}

	// Generate textarea default value and if input is disabled
	const textareaVal = userCanWrite
		? t.chat.inputPlaceholder
		: t.chat.inputDisabled;

	return (
		<form
			className="chat-input-container"
			id="chat-input-container"
			onSubmit={handleSubmit}
		>
			<textarea
				className="chat-input input"
				id="chat-input"
				placeholder={textareaVal}
				rows="1"
				maxLength={1000}
				onChange={handleChange}
				value={messageContent}
				disabled={!userCanWrite}
				onKeyDown={handleKeyDown}
				ref={textareaRef}
			/>
			<button
				className="send-btn btn btn-secondary"
				id="send-btn"
				type="submit"
				disabled={!userCanWrite}
			>
				<span className="btn-text">{t.chat.sendButton}</span>
				<span className="btn-icon">➤</span>
			</button>
		</form>
	);
	}
