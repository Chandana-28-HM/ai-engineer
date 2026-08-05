import InputBox from "@/components/InputBox";

export default function ChatArea() {
  return (
    <div className="flex flex-col flex-1">
      <div className="flex-1 p-4">
        <h2 className="text-xl font-semibold">
          Welcome to AI Engineer
        </h2>
      </div>

      <InputBox />
    </div>
  );
}