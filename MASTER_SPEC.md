# Deal Intelligence Agent

You are a senior software architect, data engineer, ML engineer, product designer and quantitative analyst.

Your task is to build a production-ready Deal Intelligence Agent.

## Mission

The goal is NOT to find discounts.

The goal is to find exceptional opportunities.

The system should optimize for:

- Real financial value
- Historical price deviation
- Rarity
- Product quality
- Personal relevance
- Regret if missed

The system should behave like:

- Professional arbitrage trader
- Data analyst
- Coupon expert
- Personal shopping assistant

I prefer 1 phenomenal deal per week over 100 average deals per day.

---

# Architecture Requirements

Build a modular Python project.

Use:

- Python
- GitHub Actions
- Telegram
- Configuration files
- Local storage (free-first architecture)

The solution must be expandable to:

- PostgreSQL
- Supabase
- Discord
- WhatsApp
- Microsoft Teams
- Email
- Browser Extensions
- Mobile Apps

---

# Data Sources

Design a connector architecture.

Initial connectors:

- Pepper RSS
- iBood
- Steam Deals

Future connectors:

- Amazon
- Bol
- Coolblue
- MediaMarkt
- Zalando
- Nike
- Adidas
- Booking
- Airbnb
- KLM
- Ryanair
- Ticketmaster
- Eventim
- Thuisbezorgd
- Uber Eats

Connectors must be easy to add.

---

# Deal Score

Calculate a Deal Score between 0 and 100.

Components:

Historical Price Score:
30%

Quality Score:
20%

Savings Score:
15%

Scarcity Score:
15%

Personal Relevance Score:
10%

Regret Score:
10%

Final score:
weighted average.

---

# Deal Classifications

100:
Legendary

95-99:
No Brainer

90-94:
God Tier

85-89:
Insanely Good

80-84:
Exceptional

Below 80:
Ignore

---

# Historical Price Engine

Create a dedicated abstraction layer.

Responsibilities:

- Historical lows
- Historical averages
- Price anomaly detection
- Fake discount detection
- Lowest known price tracking

Initially support mock historical data.

Must be replaceable with real databases later.

---

# Quality Engine

Calculate a quality score.

Use:

- Brand recognition
- Community popularity
- Review signals

Architecture should allow future integrations with:

- Amazon Reviews
- Reddit
- Tweakers
- Wirecutter
- RTINGS

---

# Personal Profile Engine

Create a profile system.

Profile contains:

- Preferred brands
- Preferred categories
- Preferred stores
- Interests

Example:

{
  "technology": 1.0,
  "travel": 0.9,
  "football": 0.8,
  "gaming": 0.7
}

The system should reward relevant deals.

---

# Regret Engine

Create a module that estimates:

"How much would a rational consumer regret missing this deal?"

Return score 0-100.

Initially implement rule-based logic.

Make it replaceable with AI later.

---

# Best Friend Test

Before sending a deal, run this test:

"Would an extreme value expert actively recommend this deal to their best friend?"

If NO:
reject deal.

If YES:
continue.

Create a dedicated module.

---

# Notification Rules

Score >=95

Immediate Telegram notification.

Score 90-94

Daily digest.

Score 80-89

Weekly digest.

Below 80

No notifications.

---

# Telegram Format

Every notification must include:

- Product
- Store
- Current price
- Estimated normal price
- Historical low
- Euro savings
- Percentage savings
- Deal score
- Classification
- Why exceptional
- Probability of return
- Action recommendation

Action recommendation must be one of:

- Buy Now
- Strongly Consider
- Watch
- Ignore

---

# GitHub Actions

Create workflow:

- Manual trigger
- Daily scheduled execution

---

# Deliverables

Generate:

- Complete project structure
- Python source code
- Configuration files
- README
- GitHub Actions workflow
- Example profile
- Example connectors

The code should be clean, modular and production-oriented.

Start with a fully working MVP.
Avoid overengineering.
Focus on 80/20 value.
