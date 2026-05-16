/*
Use of this file is as follows :
Client Request -> Helmet middleware -> CORS middleware -> 
JSON parser -> Rate Limiter -> Route Handler -> response sent back 
*/


const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const limiter = require("express-rate-limit");

const app = express();

app.use(cors({ origin: process.env.FRONTEND_URL }));
app.use(helmet());
app.use(rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    message: "Too many requests from this IP, please try again later",
}))

app.use(express.json());
app.use('/api/', limiter)

// Health here checks the server health and lets us know if the server/api is running
app.get("/health", (req, res) => {
    res.json({ status: "ok" });
})

module.exports = app;