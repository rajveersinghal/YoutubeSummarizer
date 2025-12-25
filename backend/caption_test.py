from services.youtube_captions import get_youtube_captions
import time
import re


def test_video(video_id, title="User Video"):
    """Test a single YouTube video"""
    print(f"\n📹 {title} ({video_id})")
    
    try:
        transcript = get_youtube_captions(video_id)
        
        if transcript:
            print(f"   ✅ SUCCESS! {len(transcript)} chars")
            print(f"   Preview: {transcript[:200]}...")
        else:
            print(f"   ❌ No captions available")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print()


def main():
    print("🧪 YouTube Caption Service Tester\n")
    print("=" * 60)
    
    while True:
        print("\n📝 Options:")
        print("  1. Test a YouTube video")
        print("  2. Test preset videos")
        print("  3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            video_input = input("\n🔗 Enter YouTube URL or Video ID: ").strip()
            
            # Extract video ID from URL or use as-is
            if "youtube.com" in video_input or "youtu.be" in video_input:
                match = re.search(r'(?:v=|/)([A-Za-z0-9_-]{11})', video_input)
                if match:
                    video_id = match.group(1)
                else:
                    print("❌ Invalid YouTube URL")
                    continue
            else:
                video_id = video_input
            
            title = input("📌 Enter a title (optional, press Enter to skip): ").strip() or "User Video"
            
            test_video(video_id, title)
            
        elif choice == "2":
            test_videos = [
                ('3TGqlQxpuU0', 'Prompts in LangChain'),
                ('dQw4w9WgXcQ', 'Rick Roll'),
                ('9bZkp7q19f0', 'Gangnam Style'),
                ('jNQXAC9IVRw', 'First YouTube Video'),
            ]
            
            print("\n🎬 Testing Preset Videos...")
            print("=" * 60)
            print("⏳ Adding delays to avoid rate limits...\n")
            
            for i, (video_id, title) in enumerate(test_videos, 1):
                test_video(video_id, title)
                
                # Add delay between requests to avoid rate limiting
                if i < len(test_videos):
                    print(f"⏸️  Waiting 5 seconds before next video...")
                    time.sleep(5)
            
            print("=" * 60)
        
        elif choice == "3":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
