const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const pool = require("../db/postgres.js");

/* jwt has header, payload and signature
 payload has user id and expiration time, signature is used for verification
 secret is used for signing and verification
 */

const generateToken = (userID) => {
    return jwt.sign(
        { id: userID },
        process.env.JWT_SECRET,
        { expiresIn: process.env.JWT_EXPIRES_IN }
    )
}


//Checking if user exists in Database, if not write the details to the Database
const register = async (req, res) => {
    try {
        const { email, username, password } = req.body;
        const existingUser = await pool.query(
            'SELECT id, username, email FROM users WHERE email = $1 OR username = $2',
            [email, username]
        )

        if (existingUser.rows.length > 0) {
            return res.status(409).json({ message: 'Email or UserName already exists' });
        }

        const hashedPassword = await bcrypt.hash(password, 12);

        const result = await pool.query(
            `INSERT INTO users (email, username, password)
        VALUES ($1, $2, $3)
        RETURNING id, email, username, created_at`,
            [email, username, hashedPassword]
        );

        const user = result.rows[0];
        const token = generateToken(user.id);

        res.status(201).json({
            message: "User registered successfully",
            user: {
                id: user.id,
                email: user.email,
                username: user.username,
            },
            token
        });

    } catch (error) {
        console.error('Registration error:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
}

/*Checking if User exists and matching password
 if user exists, create a token
 return a success response to the user
*/
const login = async (req, res) => {
    try {
        const { email, password } = req.body;

        const result = await pool.query(
            'SELECT * FROM users WHERE email = $1',
            [email]
        );

        const user = result.rows[0];

        if (!user || !(await bcrypt.compare(password, user.password))) {
            return res.status(401).json({ message: "Invalid username or password" });
        }

        const token = generateToken(user.id);

        res.status(201).json({
            message: "User logged in successfully",
            user: {
                id: user.id,
                email: user.email,
                username: user.username,
            },
            token
        });


    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
}


module.exports = { register, login };