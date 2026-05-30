import sys
from playwright.sync_api import sync_playwright

def execute_aarogya_protocol():
    print("🌐 Launching high-reliability Playwright browser engine...")
    
    with sync_playwright() as p:
        # Launching a physical Chromium instance so you and viewers can watch the automation live
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        
        url = "http://127.0.0.1:5173"
        print(f"🔗 Navigating directly to local dashboard: {url}")
        
        try:
            # Navigate and wait for the base network requests to settle down
            page.goto(url, wait_until="load", timeout=15000)
        except Exception as e:
            print(f"\n❌ CRITICAL: Could not reach the Vite server at {url}.")
            print("👉 Ensure your frontend development server is actively running in your other terminal tab via 'npm run dev'!")
            browser.close()
            sys.exit(1)
            
        print("⏱️ Waiting for dashboard UI elements to sync...")
        # Explicit safety check: Ensure the critical Quick Action button is fully rendered
        page.wait_for_selector("text=Call Prachi", timeout=10000)
        
        print("\n▶️ Step 1: Locating and clicking the timeline Play button...")
        # Attempts to locate a button containing 'Play' or fallback icons near the top of your layout
        play_button = page.get_by_role("button").filter(has_text="Play").first
        if not play_button.is_visible():
            # Fallback locator if it uses an icon asset or specific class
            play_button = page.locator("button:has(svg), .play-btn, [id*='play']").first
            
        play_button.click()
        print("✅ Play button successfully triggered.")
        
        print("\n⏳ Step 2: Holding for 2 seconds to allow React state updates...")
        page.wait_for_timeout(2000)
        
        print("\n🚨 Step 3: Triggering emergency 'Call Prachi' Quick Action protocol...")
        # Directly targets the specific button text from your dashboard rules
        call_button = page.get_by_text("Call Prachi", exact=False)
        call_button.click()
        print("✅ Emergency call action executed successfully!")
        
        print("\n🎉 Demonstration sequence executed flawlessly! Keeping browser open for verification...")
        page.wait_for_timeout(5000)
        
        browser.close()

if __name__ == "__main__":
    execute_aarogya_protocol()