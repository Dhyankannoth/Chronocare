require("dotenv").config();
const app = require("./src/app.js");
require("./src/db/postgres.js");

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
    console.log(`Chronocare api is running on port ${PORT}`);
});

