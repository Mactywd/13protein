import Message from "../Message/Message";

import "./Chat.css";

export default function Chat({ messages, chatBottomRef, messageRefs, setUserCanWrite }) {
    const finalMessageIndex = messages.length - 1;

    return (
        <div className="chat-messages" id="chat-messages">
            {messages.map((data, index) => (
                <div
                    key={index}
                    ref={el => {
                        if (messageRefs && el) {
                            messageRefs.current[index] = el;
                        }
                    }}
                    style={{ display: "flex"}}
                >
                    <Message
                        data={data}
                        isLastMessage={index === finalMessageIndex}
                        setUserCanWrite={setUserCanWrite}
                    />
                </div>
            ))}
            <div id="chat-end"></div>
            <div className="chat-end-spacer" ref={chatBottomRef}></div>
        </div>
    )
}