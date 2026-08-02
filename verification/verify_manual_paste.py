import sys
import os
from playwright.sync_api import sync_playwright

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Log browser console & errors
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.on("pageerror", lambda err: print(f"BROWSER PAGEERROR: {err.message}"))

        # Go to local dev server
        page.goto("http://localhost:3000")

        # Click the semi-auto mode button
        page.click("#mode-toggle")

        # Select "Manual Paste Prediction" in the league select dropdown
        page.select_option("#semi-league-select", "manual")

        # Fill in Step 1
        page.fill("#manual-league-name", "Eliteserien Manual")
        page.fill("#manual-home-name", "Brann")
        page.fill("#manual-away-name", "Viking")
        page.click("#manual-to-step-2")

        # Fill in Step 2: Home Paste (Brann)
        home_paste_data = """Viking 4th
(H) 20th Jul
1.2-0.8
Molde 2nd
(A) 12th Jul
2.1-1.5
Kilmarnock 10th
(H) 5th Jul
3.0-1.1
Aberdeen 3rd
(A) 28th Jun
0.5-2.2"""
        page.fill("#manual-home-paste", home_paste_data)
        page.click("#manual-to-step-3")

        # Capture screenshot of Home confirmation (Step 3)
        page.wait_for_selector("#manual-home-parsed-list .parsed-match-item")
        page.screenshot(path="/home/jules/verification/home_confirm.png")
        print("Home confirmation screenshot saved.")

        # Click next to Step 4
        page.click("#manual-to-step-4")

        # Fill in Step 4: Away Paste (Viking)
        away_paste_data = """Brann 6th
(A) 20th Jul
1.2-0.8
Bodø/Glimt 1st
(H) 14th Jul
1.5-1.5
Lillestrøm 11th
(A) 7th Jul
0.8-2.0
Sandefjord 12th
(H) 1st Jun
2.2-0.4"""
        page.fill("#manual-away-paste", away_paste_data)
        page.click("#manual-to-step-5")

        # Capture screenshot of Away confirmation (Step 5)
        page.wait_for_selector("#manual-away-parsed-list .parsed-match-item")
        page.screenshot(path="/home/jules/verification/away_confirm.png")
        print("Away confirmation screenshot saved.")

        # Click Save & Predict
        page.click("#manual-save-predict")

        # Wait for success alert
        page.wait_for_selector(".alert-message.success")

        # Capture screenshot of final screen with the success alert
        page.screenshot(path="/home/jules/verification/prediction_success.png")
        print("Prediction success screenshot saved.")

        success_text = page.inner_text(".alert-message.success")
        print(f"Success Text: {success_text}")

        # Print actual parsed items from the DOM for Brann
        home_parsed_items = page.eval_on_selector_all("#manual-home-parsed-list .parsed-match-item", "items => items.map(el => el.innerText)")
        print("\nParsed Home Matches (Brann) in UI:")
        for idx, text in enumerate(home_parsed_items):
            print(f"Match {idx+1}:\n{text}\n")

        browser.close()

if __name__ == "__main__":
    run_verification()
