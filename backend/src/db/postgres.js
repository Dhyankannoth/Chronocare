const { Pool } = require("pg");

const pool = new Pool({
    host: process.env.PG_HOST,
    port: process.env.PG_PORT,
    database: process.env.PG_DATABASE,
    user: process.env.PG_USER,
    password: process.env.PG_PASSWORD,
})

pool.connect((err, client, release) => {
    if (err) {
        console.error('PostgreSQL connection error:', err.message);
    } else {
        console.log('PostgreSQL connected successfully');
        release();
    }
});

module.exports = pool;