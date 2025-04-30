// frontend/src/components/Progress.tsx
import React, { useEffect, useState } from "react";

type Stage = "interpret" | "fetch" | "convert" | "viz" | "finish";

const steps: Stage[] = ["interpret", "fetch", "convert", "viz", "finish"];

export default function Progress({ taskId }: { taskId: string }) {
  const [current, setCurrent] = useState<Stage>("interpret");
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const es = new EventSource(`/agent/sse?task_id=${taskId}`);
    es.onmessage = (e) => {
      if (e.data.startsWith("{")) {
        const obj = JSON.parse(e.data);
        if (obj.step && obj.status) setCurrent(obj.step);
        if (obj.msg) setLogs((l) => [...l, obj.msg]);
      }
    };
    return () => es.close();
  }, [taskId]);

  const pct =
    (steps.findIndex((s) => s === current) / (steps.length - 1)) * 100;

  return (
    <div className="space-y-2">
      <div className="w-full bg-gray-200 h-2 rounded">
        <div
          className="bg-blue-500 h-2 rounded transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <pre className="text-xs max-h-40 overflow-y-auto bg-black text-green-300 p-2 rounded">
        {logs.join("\n")}
      </pre>
    </div>
  );
}
