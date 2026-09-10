import { useContext, useEffect, useState } from "react";
import ConversationContext from "../../contexts/ConversationContext";
import TypingIndicator from "./TypingIndicator";

import "./Message.css";

/* Message has to have this data:
{
    "sender": "user/ai",
    "type": "text/choice/carousel/typing",
    "additionalClasses": ["class1", "class2"],
    "payload": {
        **IF TEXT**
        "message": "..."

        **IF CHOICE**
        "buttons": [
            {
                "name": "...",
                "request": {...}
            },
            {
                "name": "...",
                "request": {...}
            }
        ]

        **IF CAROUSEL**
        "cards": [
            {
                "title": "...",
                "description": {...},
                "imageUrl": "...",
                "request": {...}
            },
            ...  
        ]

        **IF TYPING**
        (empty payload)
    }
}
*/

export default function Message({ data, isLastMessage, setUserCanWrite, fullMeta = true }) {
    const { sender, type, payload, additionalClasses = [] } = data;
    var classes = ['message', sender, ...additionalClasses].join(' ');

    const { meta } = data;

    function formatTooltip() {
        if (!meta) return null;
        const lines = [];
        if (meta.created_at) {
            lines.push(new Date(meta.created_at).toLocaleString('it-IT',
                { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        }
        if (fullMeta && sender === 'ai' && type === 'text') {
            if (meta.prompt_tokens != null || meta.completion_tokens != null) {
                lines.push(`Token: ${meta.prompt_tokens ?? 0} in / ${meta.completion_tokens ?? 0} out`);
            }
            if (meta.cost != null) lines.push(`Costo: $${Number(meta.cost).toFixed(5)}`);
            if (meta.model) lines.push(`Modello: ${meta.model}`);
        }
        return lines.length ? lines : null;
    }

    const tooltipLines = formatTooltip();
    const [ isDisabled, setIsDisabled ] = useState(false)
    const [ clickedCardIndex, setClickedCardIndex ] = useState(null)
    
    const { 
        handleMessageSend: sendMessage,
        handleEnd: onEnd
    } = useContext(ConversationContext);

    const customStylingContent = [
        "altro",
        "other",

        "concludi il tuo sogno",
        "finish your dream",
    ]
    
    // HANDLE ON END
    useEffect(() => {
        if (type === "end") {
            onEnd();
        }
    }, [type, onEnd])

    // INITIALIZE
    if (!data) {
        return null;
    }
    
    // HANDLERS
    function handleButtonClick(button) {
        setIsDisabled(true)
        const messagePayload = {
            type: "text",
            sender: "user",
            payload: {
                // Show the friendly label, send the backend value.
                message: button.name,
                sendValue: button.request.payload.label
            }
        }
        sendMessage(messagePayload);
        setUserCanWrite(false);
    }
    function handleCarouselClick(card, cardIndex) {
        setClickedCardIndex(cardIndex)
        const messagePayload = {
            type: "text",
            sender: "user",
            payload: {
                // Show the card title, send the backend value.
                message: card.title,
                sendValue: card.buttons[0].name
            }
        }
        sendMessage(messagePayload)
        setUserCanWrite(false);
    }

    // RENDER
    function renderText() {
        const formatMessage = (text) => text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        return (
            <div className={classes + (tooltipLines ? ' has-tooltip' : '')}>
                <p dangerouslySetInnerHTML={{ __html: formatMessage(payload.message) }}></p>
                {tooltipLines && (
                    <span className="message-tooltip">
                        {tooltipLines.map((l, i) => <span key={i}>{l}</span>)}
                    </span>
                )}
            </div>
        );
    }
    
    function renderButtons() {
        if (!classes.includes('message-buttons-only')) {
            classes += ' buttons-only';
        }

        var disabledClass = ""
        if (isDisabled || !isLastMessage) {
            disabledClass += "disabled"
        }

        return (
            <div className={classes}>
                <div className={"message-buttons " + disabledClass}>
                    {
                        payload.buttons.map((button, index) => (
                            <button
                                key={index}
                                className={"message-button btn btn-secondary" + (customStylingContent.includes(button.name.toLowerCase()) ? " custom-btn" : "")}
                                onClick={() => handleButtonClick(button)}
                            >{button.name}</button>
                        ))
                    }
                </div>
            </div>
        );
    }

    function renderCarousel() {
        if (!classes.includes('carousel-only')) {
            classes += ' carousel-only';
        }

        return (
            <div className={classes}>
                <div className="message-carousel">
                    {
                        payload.cards.map((card, index) => {
                            var clickedClass;
                            var onClickFunction = () => {};

                            if (clickedCardIndex !== null) {
                                if ( clickedCardIndex == index) {
                                    clickedClass = "selected"
                                } else {
                                    clickedClass = "dimmed"
                                }
                            
                            } else {    
                                onClickFunction = () => handleCarouselClick(card, index);
                            }

                            if (payload.cards.length === 1) {
                                clickedClass += " showcase"
                            }

                            return (
                            <div key={index} className={"message-card " + clickedClass} onClick={onClickFunction}>
                                {card.imageUrl && <img className="card-image" src={card.imageUrl} alt={card.title} />}
                                <div className="card-title">{card.title}</div>
                                <div className="card-description">{card.description.text}</div>
                            </div>)
                        })
                    }
                </div>
            </div>
        );
    }

    function renderTyping() {
        return <TypingIndicator variants={payload.variants} />;
    }

    // RENDER BASED ON TYPE
    switch (type) {
        case 'text':
            return renderText();
        case 'choice':
            return renderButtons();
        case 'carousel':
            return renderCarousel();
        case 'typing':
            return renderTyping();
    }
}