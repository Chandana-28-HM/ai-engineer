type Props = {
  role: "user" | "assistant";
  content: string;
};

export default function MessageBubble({ role, content }: Props) {
  return (
    <div className="mb-3">
      <strong>{role}:</strong> {content}
    </div>
  );
}