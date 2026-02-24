import { GameShell } from "@/src/components/GameShell";

type Props = { params: Promise<{ sessionId: string }> };

export default async function GameSessionPage({ params }: Props) {
  const { sessionId } = await params;
  return <GameShell spectatorSessionId={sessionId} />;
}
