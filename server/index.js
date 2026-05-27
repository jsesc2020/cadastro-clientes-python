const express = require('express')
const path = require('path')
const cors = require('cors')
const knex = require('./knex')
const authRoutes = require('./routes/auth')
const collaboratorRoutes = require('./routes/collaborators')

const app = express()
app.use(cors())
app.use(express.json())

app.use('/api/auth', authRoutes)
app.use('/api/collaborators', collaboratorRoutes)

app.use(express.static(path.join(__dirname, '../dist')))

const port = process.env.PORT || 4000
app.listen(port, () => console.log(`Server running on http://localhost:${port}`))
