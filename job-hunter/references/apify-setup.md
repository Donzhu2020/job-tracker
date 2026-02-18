# Apify Setup Guide

This guide explains how to set up Apify for job scraping.

## Getting Your API Key

1. Go to [Apify Console](https://console.apify.com/)
2. Sign up or log in
3. Navigate to **Account** → **Integrations**
4. Copy your **API Token**

## Apify Actors Used

### LinkedIn Jobs Scraper
- **Actor ID:** `curious_coder/linkedin-jobs-scraper`
- **URL:** https://apify.com/curious_coder/linkedin-jobs-scraper
- **Pricing:** Pay-per-result, typically $0.10-0.50 per 100 jobs

### Indeed Scraper
- **Actor ID:** `misceres/indeed-scraper`
- **URL:** https://apify.com/misceres/indeed-scraper
- **Pricing:** Pay-per-result, typically $0.10-0.30 per 100 jobs

## Configuring Search URLs

For more precise results, you can configure direct search URLs instead of relying on keyword-based search.

### LinkedIn Search URL

1. Go to [LinkedIn Jobs](https://www.linkedin.com/jobs/)
2. Enter your search criteria:
   - Keywords
   - Location
   - Date posted
   - Experience level
   - Job type
   - Remote options
3. Copy the URL from your browser
4. Use this URL in your config's `linkedin_search_url` field

Example URL:
```
https://www.linkedin.com/jobs/search/?currentJobId=123&f_E=3%2C4&f_JT=F&f_TPR=r604800&f_WT=2&geoId=102095887&keywords=software%20engineer&location=San%20Francisco%20Bay%20Area
```

URL Parameters:
- `f_E=3,4` - Experience level (3=Associate, 4=Mid-Senior)
- `f_JT=F` - Job type (F=Full-time)
- `f_TPR=r604800` - Time posted (r604800=past week)
- `f_WT=2` - Workplace type (2=Remote)
- `geoId=102095887` - Location ID

### Indeed Search URL

1. Go to [Indeed](https://www.indeed.com/)
2. Enter your search criteria
3. Apply filters (date posted, salary, job type, etc.)
4. Copy the URL from your browser
5. Use this URL in your config's `indeed_search_url` field

Example URL:
```
https://www.indeed.com/jobs?q=software+engineer&l=San+Francisco%2C+CA&radius=25&fromage=7&sc=0kf%3Aattr(DSQF7)%3B
```

URL Parameters:
- `q` - Search query
- `l` - Location
- `radius` - Miles radius
- `fromage` - Days since posted (7=past week)
- `sc` - Filters (remote, job type, etc.)

## Rate Limits & Costs

### Free Tier
- Apify provides $5 free credits monthly
- Sufficient for ~50-100 job scrapes

### Paid Plans
- Pay-as-you-go: $0.10-0.50 per actor run
- Subscription plans available for heavy usage

### Recommendations
- Set `posted_within_days` to 7 to avoid re-scraping old jobs
- Use specific search URLs to reduce unnecessary results
- Run daily rather than hourly to minimize costs

## Troubleshooting

### "Actor run failed"
- Check if you have sufficient Apify credits
- Verify the actor is still available and not deprecated
- Check if LinkedIn/Indeed has changed their site structure

### "No results found"
- Verify your search URL returns results in a browser
- Try broadening your search criteria
- Check if the website is blocking the scraper (rate limiting)

### "Rate limited"
- Reduce scraping frequency
- Use residential proxies (enabled by default in config)
- Add delays between requests if running multiple searches

## Data Format

Jobs are returned in a normalized format:

```json
{
  "id": "abc123def456",
  "source": "linkedin",
  "title": "Senior Software Engineer",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "description": "Full job description...",
  "url": "https://linkedin.com/jobs/view/...",
  "posted_date": "2025-01-20T00:00:00",
  "salary": "$150,000 - $200,000",
  "employment_type": "Full-time",
  "experience_level": "Mid-Senior",
  "remote": true,
  "scraped_at": "2025-01-27T10:30:00"
}
```
