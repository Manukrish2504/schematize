Create these files, then use schematize to diagram this project.

`package.json`
```json
{ "name": "notes", "dependencies": { "express": "^4", "pg": "^8", "ioredis": "^5", "openai": "^4" } }
```

`server.js`
```js
const app = require("express")();
const db = new (require("pg").Pool)({ connectionString: process.env.DATABASE_URL });
const cache = new (require("ioredis"))(process.env.REDIS_URL);
const openai = new (require("openai"))();
app.get("/notes/:id", async (req, res) => res.json(await cache.get(req.params.id) || (await db.query("select * from notes where id=$1", [req.params.id])).rows[0]));
app.post("/notes/:id/summary", async (req, res) => res.json(await openai.chat.completions.create({ model: "gpt-4o", messages: [] })));
app.listen(3000);
```
