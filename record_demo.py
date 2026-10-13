import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright

async def run():
    print("Launching playwright browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        print("Navigating to http://localhost:8080...")
        await page.goto("http://localhost:8080")
        await page.wait_for_selector("#input")
        await asyncio.sleep(2)

        # Start ffmpeg recording
        video_out = "/config/Desktop/BuildWithGemini/demo_travel_planner.mp4"
        if os.path.exists(video_out):
            os.remove(video_out)

        print("Starting ffmpeg screen recording...")
        ffmpeg_proc = subprocess.Popen([
            "ffmpeg", "-y",
            "-video_size", "1280x800",
            "-framerate", "25",
            "-f", "x11grab",
            "-i", ":1.0+0,0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            video_out
        ])

        try:
            await asyncio.sleep(2)

            # Prompt 1: What the app does best - personalized itinerary recommendation with safety/dietary memory check
            prompt1 = "Hi! I'm planning a 3-day romantic trip to Kyoto. I love historical temples and traditional gardens. Can you recommend an itinerary?"
            print(f"Typing prompt 1: {prompt1}")
            await page.fill("#input", prompt1)
            await asyncio.sleep(1)
            await page.click("button")

            print("Waiting for agent response to prompt 1...")
            # Wait for assistant message bubble
            await page.wait_for_selector(".msg.assistant, .bubble", timeout=120000)
            # Give it time to fully render cards/text
            await asyncio.sleep(10)

            # Scroll log to bottom
            await page.evaluate("document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight")
            await asyncio.sleep(3)

            # Prompt 2: Richer prompt showing off a tool call, database lookup, and image generation
            prompt2 = "That looks fantastic! Can you look up details for Kyoto in the database and generate a scenic visual illustration for our trip?"
            print(f"Typing prompt 2: {prompt2}")
            await page.fill("#input", prompt2)
            await asyncio.sleep(1)
            await page.click("button")

            print("Waiting for agent response to prompt 2 (tools + image generation)...")
            # Wait for the next reply to finish
            await asyncio.sleep(30)
            # Scroll again
            await page.evaluate("document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight")
            await asyncio.sleep(10)

        finally:
            print("Stopping ffmpeg recording...")
            ffmpeg_proc.terminate()
            try:
                ffmpeg_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                ffmpeg_proc.kill()
            await browser.close()

    print("Demo video recorded successfully to:", video_out)

if __name__ == "__main__":
    asyncio.run(run())
