const worker = new Worker(new URL("./worker.ts", import.meta.url), {
  type: "module",
});
let sequence = 0;
const pending = new Map<
  number,
  { resolve: (v: any) => void; reject: (e: Error) => void }
>();
worker.onmessage = ({ data }) => {
  const p = pending.get(data.id);
  if (!p) return;
  pending.delete(data.id);
  if (data.error) p.reject(new Error(data.error));
  else p.resolve(data.result);
};
worker.onerror = () => {
  for (const p of pending.values())
    p.reject(new Error("存档处理线程异常，请重新打开页面"));
  pending.clear();
};
export function request<T>(
  type: string,
  slot = 0,
  payload?: unknown,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const id = sequence++;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, slot, payload });
  });
}
export function download(
  bytes: Uint8Array | string,
  filename: string,
  type = "application/octet-stream",
) {
  const data = typeof bytes === "string" ? bytes : bytes.slice().buffer;
  const url = URL.createObjectURL(new Blob([data], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
