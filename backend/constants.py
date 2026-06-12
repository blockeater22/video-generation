PLAN_CREDITS = {"free": 3, "starter": 50, "pro": 300, "enterprise": 1_000_000}
PLAN_PRICES = {"starter": 29.00, "pro": 99.00}

OPENAI_VOICES = ["alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"]
OPENAI_VOICE_FALLBACK = {"female": "nova", "male": "onyx"}

STOCK_AVATARS = [
    {"name": "Sofia (Professional)", "thumbnail_url": "https://images.unsplash.com/photo-1573497161161-c3e73707e25c?w=600&q=80", "gender": "female"},
    {"name": "Marcus (Corporate)", "thumbnail_url": "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=600&q=80", "gender": "male"},
    {"name": "Aria (Presenter)", "thumbnail_url": "https://images.unsplash.com/photo-1685760259914-ee8d2c92d2e0?w=600&q=80", "gender": "female"},
    {"name": "Lena (Cinematic)", "thumbnail_url": "https://images.unsplash.com/photo-1532171875345-9712d9d4f65a?w=600&q=80", "gender": "female"},
    {"name": "David (Newsdesk)", "thumbnail_url": "https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=600&q=80", "gender": "male"},
    {"name": "Maya (Educator)", "thumbnail_url": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=600&q=80", "gender": "female"},
]

STOCK_VOICES = [
    {"name": "Emma", "language": "en", "gender": "female", "engine": "openai_tts", "openai_voice": "nova"},
    {"name": "James", "language": "en", "gender": "male", "engine": "openai_tts", "openai_voice": "onyx"},
    {"name": "Sophie", "language": "en", "gender": "female", "engine": "openai_tts", "openai_voice": "shimmer"},
    {"name": "Carlos", "language": "es", "gender": "male", "engine": "openai_tts", "openai_voice": "echo"},
    {"name": "Yuki", "language": "ja", "gender": "female", "engine": "openai_tts", "openai_voice": "coral"},
    {"name": "Liam", "language": "en", "gender": "male", "engine": "openai_tts", "openai_voice": "ash"},
]
