# TELEPAT persistent Memory service

The production Memory blocker is implemented as an independent Modal app:

`quantareon-telepat-memory`

It implements the existing stable TELEPAT remote-memory contract:

- `POST /api/recall`
- `POST /api/store`

## Persistence

The service stores exchanges in SQLite on the persistent Modal Volume:

`quantareon-telepat-memory`

The web function is capped at one container, avoiding concurrent writers to the
same SQLite file. After each write the mounted Modal Volume is explicitly
committed so the database survives container replacement.

Each user is isolated by TELEPAT's stable legacy numeric memory id and history
is bounded per user. The first implementation uses deterministic token overlap
plus recency for semantic recall; richer embeddings/vector search can replace
this implementation later without changing the `MemoryAdapter` contract.

## Authentication

Recall and store require:

`Authorization: Bearer <MEMORY_API_KEY>`

The deploy workflow generates a high-entropy key, masks it in GitHub Actions,
writes the same key into the Memory app Secret and TELEPAT provider Secret, and
never commits the value to the repository.

## Deployment

`TELEPAT Memory Deploy` performs the complete chain:

1. provision the Memory app Secret;
2. deploy the persistent Memory API;
3. store and recall a unique smoke exchange;
4. configure TELEPAT's `MEMORY_API_URL` and auth;
5. redeploy the TELEPAT CPU app;
6. run the deployed TELEPAT provider probe.

This service is intentionally separate from the in-process SessionStore.
Session state remains ephemeral conversational state; Memory is durable
cross-session user context.
