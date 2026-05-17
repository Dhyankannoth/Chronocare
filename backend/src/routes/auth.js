const jwt = require("jsonwebtoken");
const Joi = require("joi");
const { register, login } = require("../controllers/authController");
const express = require("express");
const router = express.Router();

const registerSchema = Joi.object({
    email: Joi.string().email().required(),
    username: Joi.string().min(3).max(30).required(),
    password: Joi.string().min(8).required(),
});

const loginSchema = Joi.object({
    email: Joi.string().email().required(),
    password: Joi.string().required(),
});

const validate = (schema) => (req, res, next) => {
    const { error } = schema.validate(req.body);
    if (error) {
        return res.status(400).json({ error: error.details[0].message });
    }
    next();
};

router.post('/register', validate(registerSchema), register);
router.post('/login', validate(loginSchema), login);

module.exports = router;
