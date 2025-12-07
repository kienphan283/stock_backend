import { Server } from "socket.io";
import { logger } from "../utils";

export class SocketService {
    private io: Server;

    constructor(io: Server) {
        this.io = io;
        this.setupConnection();
    }

    private setupConnection() {
        this.io.on("connection", (socket) => {
            logger.info(`Client connected: ${socket.id}`);

            socket.on("disconnect", () => {
                logger.info(`Client disconnected: ${socket.id}`);
            });
        });
    }

    public emitMarketUpdate(data: any) {
        this.io.emit("market_update", data);
    }
}
