import { Session, type Edit } from "./core/session";
let session: Session | null = null;
self.onmessage = (event: MessageEvent) => {
  const { id, type, slot = 0, payload } = event.data;
  try {
    let result: unknown;
    if (type === "open") {
      const next = Session.open(
        new Uint8Array(payload.bytes),
        payload.filename,
      );
      session = next;
      result = next.view(next.occupied[0]);
    } else {
      if (!session) throw new Error("请先打开存档");
      switch (type) {
        case "view":
          result = session.view(slot);
          break;
        case "apply": {
          const handle = session.apply(slot, payload as Edit);
          result = { ...session.view(slot), selectedHandle: handle };
          break;
        }
        case "undo":
          session.undo();
          result = session.view(slot);
          break;
        case "redo":
          session.redo();
          result = session.view(slot);
          break;
        case "export":
          result = {
            bytes: session.export(),
            filename: session.filename,
            view: session.view(slot),
          };
          break;
        case "original":
          result = { bytes: session.original(), filename: session.filename };
          break;
        default:
          throw new Error("未知请求");
      }
    }
    self.postMessage({ id, result });
  } catch (error) {
    self.postMessage({
      id,
      error: error instanceof Error ? error.message : String(error),
    });
  }
};
