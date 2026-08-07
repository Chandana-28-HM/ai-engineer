import { Message } from "@/types/message";
import MessageBubble from "./MessageBubble";

interface ChatAreaProps {
  messages: Message[];
  loading: boolean;
}

export default function ChatArea({
  messages,
  loading,
}: ChatAreaProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          role={message.role}
          content={message.content}
        />
      ))}

      {loading && (
        <MessageBubble
          role="assistant"
          content="Thinking..."
        />
      )}
    </div>
  );
}