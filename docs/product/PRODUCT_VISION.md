# 🎯 Finance Copilot - Product Vision

## Vision Statement

**Personal Finance Copilot** - A professional-grade tool for individuals who manage their own investments but don't have time to constantly follow markets, news, and analysis.

## Target User

- **Primary**: Professional managing personal investments solo
- **Profile**: Not a finance expert, but financially literate
- **Pain Point**: Spends 3-10 hours/week researching markets, reading news, analyzing trends
- **Goal**: Make informed investment decisions quickly without becoming a market expert

## Core Value Proposition

**2-3 clicks to save 3-10 hours of research**

Users can:
- Get comprehensive market forecasts across all assets (gold, silver, AI stocks, Tesla, energy, etc.)
- Receive clear "what should I do with my portfolio today" guidance
- Ask specific questions and get deep analysis based on real-time market data
- Access multi-AI analysis with a judge mechanism to synthesize recommendations

## Key Features (Prioritized)

### MVP (Now)
1. **Live Market Data Dashboard**
   - Real-time news feed (460+ articles, auto-refresh)
   - Market forecasts with confidence scores
   - Sector performance overview

2. **Multi-AI Judge System**
   - Multiple AI models analyze same data
   - Judge synthesizes and provides final recommendation
   - Transparency: show reasoning from each model

3. **Specific Asset Forecasts**
   - Gold, Silver (precious metals)
   - AI/ Tech stocks (NVDA, TSLA, etc.)
   - Energy sector
   - Geographic/ geopolitical trends

4. **Copilot Q&A**
   - "What should I do today?"
   - "Is now a good time to buy gold?"
   - "How will Fed decision affect my portfolio?"
   - 10-minute data freshness acceptable

### BATCH-04 (Next)
5. **Daily Brief**
   - Morning briefing (5 min read)
   - Key market moves overnight
   - Action items for the day

6. **Sector Intelligence**
   - Real sector data (not mock)
   - Performance correlations
   - Rotation signals

### BATCH-05+ (Future)
7. **Portfolio Integration**
   - Connect actual holdings
   - Personalized recommendations
   - Risk assessment

8. **Advanced Analytics**
   - Backtesting engine
   - Scenario analysis
   - Risk-adjusted returns

## Technical Constraints

### Cost
- **Priority**: Low-cost or free models
- **Strategy**: Use g4f (free) as primary, Codex Pro as fallback
- **Budget**: <$50/month for personal use

### Performance
- **Response Time**: <10 seconds for standard queries
- **Data Freshness**: 10-minute gap acceptable
- **Cache**: Aggressive caching for repeated queries

### Architecture
- **Frontend**: Fast, functional, connected to live API
- **Backend**: Robust, cached, scalable
- **Data**: Real data only (no mock data in production)

## Success Metrics

### MVP Success
- [ ] Frontend shows 460+ real news articles (not 5 mock)
- [ ] Forecasts show 19+ real predictions with confidence scores
- [ ] User can get "what to do today" answer in <10 seconds
- [ ] All data is live from API (0 mock data)
- [ ] System runs on free/low-cost models (<$50/month)

### Long-term Success
- [ ] User saves 3-10 hours/week on market research
- [ ] Investment decisions made within 2-3 clicks
- [ ] Multi-AI judge provides consistent, actionable recommendations
- [ ] System covers all major assets (stocks, gold, silver, energy, geopolitics)

## Current Status

### Completed
- ✅ Backend with live news API (460 articles)
- ✅ Forecasts API (19 forecasts)
- ✅ Health endpoint operational
- ✅ Auto-recovery system active

### In Progress (BATCH-03)
- 🔧 Frontend API connector (replace mock data)
- 🔧 Data quality improvements
- 🔧 Forecasts confidence scoring

### Next (BATCH-04)
- ⏳ Daily brief generation
- ⏳ Real sector data integration

## Non-Goals (For Now)

- ❌ Social features (no sharing, no community)
- ❌ Mobile app (web-first)
- ❌ Enterprise features (personal tool)
- ❌ Deadline-driven (iterate at own pace)

---

**Last Updated**: 2026-02-28  
**Version**: 1.0  
**Status**: Active
