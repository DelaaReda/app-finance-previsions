# QA_AGENT_BRIEF.md

## Mission
Vérifier rapidement la non-régression MVP.

## Test Plan
1. `./finance-copilot.sh restart`
2. health endpoint
3. 4 endpoints data MVP
4. ouverture frontend `http://localhost:5173`
5. check console errors bloquantes

## Output Format
- PASS/FAIL par test
- erreur exacte si FAIL
- reproduction en 1-2 commandes
