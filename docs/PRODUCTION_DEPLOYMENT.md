# Production Deployment Guide

**FBP Backend NFA Automation - Deployment Checklist & Procedures**

---

## 📵 Pre-Deployment Checklist (Do First)

### Phase 1: Code Quality Validation

```bash
# 1. Run linting
cd /Users/dnigga/Documents/FBP_Backend
ruff check app/
# Expected: No errors

# 2. Run type checking
mypy app/ --strict
# Expected: No errors

# 3. Run tests
pytest tests/ -v --tb=short
# Expected: All tests PASS

# 4. Check coverage
pytest tests/ --cov=app --cov-report=term-missing
# Expected: > 80% coverage
```

### Phase 2: System Validation

```bash
# 5. Validate all NFA modules exist
./ops/validate_nfa_system.sh
# Expected: All 17 modules present ✅

# 6. Verify no hardcoded delays
grep -r "wait_for_timeout(\d+)" app/modules/nfa/*.py
# Expected: NO RESULTS (all use delays.py)

# 7. Check delays system is centralized
python3 -c "from app.modules.nfa.delays import *; print('✅ Delays OK')"
# Expected: ✅ Delays OK

# 8. Verify NOTAS_AVULSAS references removed
grep -r "NOTAS_AVULSAS" app/
# Expected: NO RESULTS
```

### Phase 3: Functionality Testing

```bash
# 9. Test NFA self-diagnostic
./ops/nfa_self_test.sh
# Expected: All diagnostics PASS ✅

# 10. Test single NFA (with test CPF)
./ops/run_nfa_now.sh single
# When prompted:
#   CPF: 73825506215
#   Login: <test_account>
#   Password: <test_password>
# Expected: NFA created, PDFs downloaded ✅

# 11. Verify output structure
ls -la output/nfa/pdf/73825506215/
# Expected: DAR.pdf, NFA.pdf present

# 12. Check logs for errors
grep ERROR logs/nfa/nfa_debug.log
# Expected: Only expected warnings, no ERRORs
```

### Phase 4: Integration Testing

```bash
# 13. Test batch processing
echo '{"destinatarios": ["73825506215"]}' > input/cpf_batch.json
./ops/run_nfa_now.sh batch
# Expected: Batch completes successfully ✅

# 14. Test API endpoints
curl -s http://localhost:8000/health
# Expected: {"status": "healthy", ...}

curl -s http://localhost:8000/api/nfa/health
# Expected: {"status": "ready", ...}

# 15. Verify database connections (if applicable)
python3 -c "from app.core.config import settings; print(f'DB: {settings.database_url}')"
# Expected: DB URL valid

# 16. Check browser availability
python3 verify.py
# Expected: Chromium version shown, M3 compatible
```

### Phase 5: Security Validation

```bash
# 17. Verify no credentials in git history
git log --all -S 'SEFAZ_PASSWORD' --oneline
# Expected: NO RESULTS (no passwords committed)

# 18. Check .gitignore covers auth files
cat .gitignore | grep -E "auth|credential|secret"
# Expected: auth/ and similar listed

# 19. Verify environment variables not in code
grep -r '"password"\|"login"\|"secret"' app/ --include="*.py"
# Expected: Only in config.py reading from env

# 20. Validate SSL/TLS for SEFAZ URLs
python3 -c "import ssl; print('SSL available')"
# Expected: SSL available
```

### Phase 6: Performance Baseline

```bash
# 21. Measure single NFA execution time
time ./ops/run_nfa_now.sh single
# Expected: < 5 minutes

# 22. Measure batch processing time
echo '{"destinatarios": ["73825506215", "12345678901", "11144477735"]}' > input/cpf_batch.json
time ./ops/run_nfa_now.sh batch
# Expected: < 15 minutes for 3 CPFs

# 23. Check memory usage
python3 -c "import psutil, os; p = psutil.Process(os.getpid()); print(f'Memory: {p.memory_info().rss / 1024 / 1024:.1f}MB')"
# Expected: < 500MB

# 24. Verify disk space usage
du -sh output/ logs/
# Expected: < 10GB total
```

---

## 🚀 Deployment Procedure

### Option 1: Local Server (Development)

```bash
# 1. Navigate to project
cd /Users/dnigga/Documents/FBP_Backend

# 2. Activate virtual environment
source ~/Documents/.venvs/fbp/bin/activate

# 3. Start server (development mode)
./scripts/dev.sh
# Output: ✅ Server running on http://localhost:8000

# 4. In another terminal, monitor logs
tail -f logs/nfa/nfa_debug.log

# 5. Server auto-reloads on code changes
# Just edit and save – no restart needed
```

### Option 2: Production Server (macOS)

```bash
# 1. SSH to production server
ssh user@prod.server.com

# 2. Navigate to project
cd /Users/username/Documents/FBP_Backend

# 3. Pull latest code
git fetch origin
git checkout main
git pull origin main

# 4. Update dependencies (if changed)
source ~/Documents/.venvs/fbp/bin/activate
pip install -e ".[dev]" --upgrade

# 5. Verify dependencies
python3 -m pip list | grep -E "fastapi|playwright|pydantic"

# 6. Run validation
./ops/validate_nfa_system.sh

# 7. Start server (production mode)
nohup ./scripts/start.sh > logs/server.log 2>&1 &
echo $! > /tmp/fbp_server.pid

# 8. Verify server started
sleep 2
curl http://localhost:8000/health

# 9. Monitor logs
tail -f logs/nfa/nfa_debug.log
```

### Option 3: Docker Deployment (Recommended)

```bash
# 1. Build Docker image (on local machine)
cd /Users/dnigga/Documents/FBP_Backend
docker build -t fbp-nfa:latest -t fbp-nfa:$(git rev-parse --short HEAD) .

# 2. Tag for registry
docker tag fbp-nfa:latest <registry>/fbp-nfa:latest

# 3. Push to registry
docker push <registry>/fbp-nfa:latest

# 4. On production server
ssh user@prod.server.com

# 5. Pull latest image
docker pull <registry>/fbp-nfa:latest

# 6. Stop old container
docker stop fbp-nfa || true
docker rm fbp-nfa || true

# 7. Start new container
docker run -d \
  --name fbp-nfa \
  -p 8000:8000 \
  -e SEFAZ_LOGIN=$SEFAZ_LOGIN \
  -e SEFAZ_PASSWORD=$SEFAZ_PASSWORD \
  -e DATABASE_URL=$DATABASE_URL \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  <registry>/fbp-nfa:latest

# 8. Verify container running
docker ps | grep fbp-nfa

# 9. Check logs
docker logs -f fbp-nfa
```

### Option 4: Kubernetes Deployment (Enterprise)

```bash
# 1. Apply ConfigMap (non-sensitive config)
kubectl apply -f k8s/configmap.yaml

# 2. Apply Secrets (sensitive data)
kubectl apply -f k8s/secrets.yaml

# 3. Apply Deployment
kubectl apply -f k8s/deployment.yaml

# 4. Apply Service
kubectl apply -f k8s/service.yaml

# 5. Verify deployment
kubectl get pods -l app=fbp-nfa
kubectl get svc fbp-nfa-service

# 6. Check logs
kubectl logs -l app=fbp-nfa -f
```

---

## 💁 Monitoring Post-Deployment

### Real-time Monitoring

```bash
# Monitor application logs
tail -f logs/nfa/nfa_debug.log

# Monitor browser console errors
tail -f logs/nfa/browser_console.log

# Monitor system resources
watch -n 1 'ps aux | grep python3 | grep -v grep'

# Monitor disk usage
watch -n 5 'du -sh output/ logs/'
```

### Metrics Collection

```bash
# Count successful NFA operations
grep "✅ NFA Created" logs/nfa/nfa_debug.log | wc -l

# Count failed operations
grep "❌ NFA Failed" logs/nfa/nfa_debug.log | wc -l

# Average execution time
grep "Execution time:" logs/nfa/nfa_debug.log | sed 's/.*: //g' | awk '{sum+=$1; count++} END {print "Average: " sum/count "ms"}'

# Error rate
FAILED=$(grep "❌ NFA Failed" logs/nfa/nfa_debug.log | wc -l)
TOTAL=$(grep "NFA" logs/nfa/nfa_debug.log | grep -E "✅|❌" | wc -l)
echo "Error rate: $(( FAILED * 100 / TOTAL ))%"
```

### Health Checks

```bash
# API health
curl -s http://localhost:8000/health | jq .

# NFA health
curl -s http://localhost:8000/api/nfa/health | jq .

# Database health
curl -s http://localhost:8000/api/db/health | jq .
```

### Alert Configuration

```bash
# Alert if error rate > 5%
# (Add to monitoring script or cron job)

FAILED=$(grep "❌ NFA Failed" logs/nfa/nfa_debug.log | tail -100 | wc -l)
TOTAL=$(grep "NFA" logs/nfa/nfa_debug.log | tail -100 | grep -E "✅|❌" | wc -l)

if [ $TOTAL -gt 0 ]; then
    ERROR_RATE=$(( FAILED * 100 / TOTAL ))
    if [ $ERROR_RATE -gt 5 ]; then
        echo "ALERT: NFA error rate $ERROR_RATE% (threshold: 5%)"
        # Send notification, trigger incident, etc.
    fi
fi
```

---

## 🔁 Rollback Procedure

If deployment causes issues:

### Rollback to Previous Version

```bash
# 1. Check git history
git log --oneline -10

# 2. Identify last known-good commit
# Example: abc1234 "NFA: Fixed login selector"

# 3. Checkout previous version
git checkout abc1234

# 4. Update dependencies (if needed)
pip install -e ".[dev]"

# 5. Restart server
./scripts/start.sh

# 6. Verify restored
curl http://localhost:8000/api/nfa/health

# 7. Investigate issue with current version
# Fix in separate branch
```

### Docker Rollback

```bash
# 1. Check image history
docker images fbp-nfa

# 2. Stop current container
docker stop fbp-nfa

# 3. Start previous version
docker run -d \
  --name fbp-nfa \
  -p 8000:8000 \
  fbp-nfa:previous-hash

# 4. Verify running
curl http://localhost:8000/health
```

---

## 🛠️ Maintenance Tasks

### Daily

```bash
# Check for errors
grep ERROR logs/nfa/nfa_debug.log | tail -50

# Verify disk space
du -sh output/ logs/

# Check system health
./ops/nfa_self_test.sh
```

### Weekly

```bash
# Analyze logs for trends
grep "Execution time:" logs/nfa/nfa_debug.log | tail -100 | \
  sed 's/.*: //g' | \
  awk '{sum+=$1; count++} END {print "Weekly avg: " sum/count "ms"}'

# Check for memory leaks
grep "Memory:" logs/nfa/nfa_debug.log | tail -20

# Rotate old logs
find logs/nfa/ -mtime +30 -delete

# Backup output PDFs
tar -czf output/nfa/backup_$(date +%Y%m%d).tar.gz output/nfa/pdf/
```

### Monthly

```bash
# Update dependencies
pip install --upgrade -e ".[dev]"

# Update Playwright browsers
python3 -m playwright install

# Run full test suite
./scripts/test.sh

# Generate performance report
# (Log analysis, error rates, execution times)
```

### Quarterly

```bash
# Update Python version
# Example: Python 3.9 -> 3.10

# Review and update security
# (Check CVEs, update vulnerable packages)

# Archive old logs
tar -czf logs/nfa/archive_2024_q3.tar.gz logs/nfa/*2024-{07,08,09}*

# Review and update documentation
```

---

## 📈 Incident Response

### NFA Creation Failing

```bash
# 1. Check recent logs
tail -100 logs/nfa/nfa_debug.log

# 2. Check SEFAZ connectivity
./ops/validate_sefaz_access.sh

# 3. Check for SEFAZ maintenance
# (Usually announced in advance)

# 4. If selector changed, update
python3 app/modules/nfa/atf_selectors.py --validate

# 5. Run diagnostics
./ops/nfa_self_test.sh

# 6. If known issue, apply patch
# (See NFA_AUTOMATION_SPECIALIST_GUIDE.md)
```

### Server Not Responding

```bash
# 1. Check if process running
ps aux | grep python3 | grep -v grep

# 2. If not running, restart
./scripts/start.sh

# 3. Check port availability
lsof -i :8000

# 4. If port occupied, find process
kill -9 $(lsof -t -i :8000)

# 5. Restart server
./scripts/start.sh

# 6. Verify health
curl http://localhost:8000/health
```

### High Memory Usage

```bash
# 1. Check memory usage
ps aux | grep python3 | grep -v grep

# 2. Identify which process
ps -A -o pid,%mem,cmd | grep python3 | sort -k2 -rn

# 3. If browser process using too much
# (Usually Playwright/Chromium)

# 4. Restart server
kill -9 <pid>
./scripts/start.sh

# 5. Monitor memory trend
watch -n 5 'ps aux | grep python3 | grep -v grep'
```

---

## 📄 Deployment Checklist Template

Use this before each deployment:

```markdown
## Deployment: [Version/Date]

### Pre-Deployment
- [ ] All tests pass (`./scripts/test.sh`)
- [ ] Code quality OK (`ruff check app/`, `mypy app/`)
- [ ] System validation passes (`./ops/validate_nfa_system.sh`)
- [ ] Single NFA test succeeds
- [ ] Batch NFA test succeeds
- [ ] No hardcoded delays (`grep -r wait_for_timeout`)
- [ ] No credential leaks
- [ ] Git history clean, no uncommitted changes

### Deployment
- [ ] Code pulled to production
- [ ] Dependencies installed/upgraded
- [ ] Server started successfully
- [ ] Health check passes
- [ ] API endpoints responding

### Post-Deployment
- [ ] Monitor logs for 1 hour
- [ ] Run 3 test NFAs
- [ ] Check error rates
- [ ] Confirm no regressions
- [ ] Alert team

### Rollback Plan (if needed)
- [ ] Previous version identified: ___________
- [ ] Rollback command ready: ___________
- [ ] Team notified: Yes / No
```

---

## 🗑️ Cleanup & Archival

### Cleanup Old Data

```bash
# Archive NFAs older than 90 days
find output/nfa/pdf/ -mtime +90 -exec tar -czf output/nfa/archive_$(date +%s).tar.gz {} \;

# Delete temp screenshots (keep 30 days)
find output/nfa/screenshots/ -mtime +30 -delete

# Archive old logs (keep 60 days)
find logs/nfa/ -mtime +60 -delete
```

### Database Cleanup (if applicable)

```bash
# Archive old records
SELECT * FROM nfa_operations WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

# Delete archived records
DELETE FROM nfa_operations WHERE created_at < DATE_SUB(NOW(), INTERVAL 180 DAY);
```

---

## 📁 Documentation Updates

After deployment, update:

1. **Changelog**: Record what was deployed
2. **Version**: Update version in `pyproject.toml`
3. **README**: Add deployment notes if needed
4. **Runbook**: Update if procedures changed

---

## 📧 Communication Template

When deploying, notify team:

```
SUBJECT: FBP Backend NFA Automation - Deployment [Version]

BODY:

Deployment Details:
- Time: [Date/Time]
- Version: [Git commit hash]
- Changes: [Brief summary]
- Impact: [Which endpoints/features affected]
- Rollback plan: [If needed to rollback]

Monitoring:
- Watch logs: tail -f logs/nfa/nfa_debug.log
- Health check: curl http://localhost:8000/health
- Status page: [URL]

Contact for issues: [Name/Slack]
```

---

**Last Updated**: 2025-12-05  
**Maintained By**: NFA_AUTOMATION_SPECIALIST_AI
