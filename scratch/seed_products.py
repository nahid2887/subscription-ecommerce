import os
import sys
import math

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from PIL import Image, ImageDraw, ImageFont
from product.models import Category, Product, ProductPlan
from django.contrib.auth.models import User

MEDIA_PROD_DIR = os.path.join('media', 'products')
os.makedirs(MEDIA_PROD_DIR, exist_ok=True)

FONT_BOLD = 'C:/Windows/Fonts/segoeuib.ttf'
FONT_REGULAR = 'C:/Windows/Fonts/segoeui.ttf'

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_pill(draw, xy, text, font, bg_color, text_color, pad_x=16, pad_y=6, radius=12):
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x, y = xy
    w = tw + pad_x * 2
    h = th + pad_y * 2
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=bg_color)
    draw.text((x + pad_x, y + pad_y - bbox[1]), text, font=font, fill=text_color)
    return w, h

def generate_banner(filename, brand_title, subtitle, badge_text, colors, icon_symbol, feature_bullets):
    W, H = 1200, 675
    img = Image.new("RGBA", (W, H), colors['bg1'] + (255,))
    
    # 1. Subtle radial gradient glow on top-right and bottom-left
    glow_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_overlay)
    
    accent_rgb = colors['accent']
    for r in range(480, 0, -15):
        alpha = int((1.0 - (r / 480.0)) * 70)
        glow_draw.ellipse([W - 320 - r, 120 - r, W - 320 + r, 120 + r], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], alpha))
    
    bg2_rgb = colors['bg2']
    for r in range(500, 0, -20):
        alpha = int((1.0 - (r / 500.0)) * 55)
        glow_draw.ellipse([-100 - r, H - 100 - r, -100 + r, H - 100 + r], fill=(bg2_rgb[0], bg2_rgb[1], bg2_rgb[2], alpha))
        
    img = Image.alpha_composite(img, glow_overlay)
    draw = ImageDraw.Draw(img)

    # 2. Modern subtle dot grid texture
    for gx in range(40, W - 40, 48):
        for gy in range(40, H - 40, 48):
            draw.point((gx, gy), fill=(255, 255, 255, 24))

    # 3. Left content area
    font_badge = get_font(FONT_BOLD, 22)
    pill_w, pill_h = draw_pill(
        draw, (80, 80), f"★ {badge_text.upper()}", font_badge,
        bg_color=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 55),
        text_color=(accent_rgb[0], accent_rgb[1], accent_rgb[2]),
        pad_x=20, pad_y=8, radius=20
    )
    draw.rounded_rectangle([80, 80, 80 + pill_w, 80 + pill_h], radius=20, outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 140), width=1)

    # Brand Title
    font_title = get_font(FONT_BOLD, 70)
    draw.text((80, 155), brand_title, font=font_title, fill=(255, 255, 255, 255))
    
    # Subtitle
    font_sub = get_font(FONT_REGULAR, 26)
    draw.text((80, 255), subtitle, font=font_sub, fill=(203, 213, 225, 255))

    # Accent line
    draw.line([(80, 310), (320, 310)], fill=colors['accent'] + (255,), width=4)

    # Bullet Points
    font_feat = get_font(FONT_BOLD, 21)
    start_y = 345
    for i, feat in enumerate(feature_bullets[:4]):
        cy = start_y + i * 44
        draw.ellipse([80, cy + 2, 102, cy + 24], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 45), outline=colors['accent'] + (220,), width=1)
        draw.text((87, cy + 3), "✓", font=get_font(FONT_BOLD, 15), fill=(colors['accent'] + (255,)))
        draw.text((116, cy + 2), feat, font=font_feat, fill=(241, 245, 249, 240))

    # Bottom Trust guarantee
    trust_font = get_font(FONT_BOLD, 20)
    draw.text((80, 565), "⚡ Instant Digital Delivery   •   🛡️ 100% Replacement Warranty", font=trust_font, fill=(148, 163, 184, 255))

    # 4. Right Card Box
    card_x1, card_y1 = W - 450, 95
    card_x2, card_y2 = W - 80, H - 95
    
    card_bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_bg)
    card_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=32, fill=(255, 255, 255, 14))
    card_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=32, outline=(255, 255, 255, 45), width=2)
    img = Image.alpha_composite(img, card_bg)
    draw = ImageDraw.Draw(img)

    cx = (card_x1 + card_x2) // 2
    cy = card_y1 + 145
    icon_r = 85
    draw.ellipse([cx - icon_r, cy - icon_r, cx + icon_r, cy + icon_r], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 45), outline=colors['accent'] + (255,), width=2)

    font_icon = get_font(FONT_BOLD, 76)
    ibox = font_icon.getbbox(icon_symbol)
    iw = ibox[2] - ibox[0]
    ih = ibox[3] - ibox[1]
    draw.text((cx - iw // 2 - ibox[0], cy - ih // 2 - ibox[1]), icon_symbol, font=font_icon, fill=(255, 255, 255, 255))

    font_card_brand = get_font(FONT_BOLD, 28)
    short_brand = brand_title.split()[0].upper()
    cbox = font_card_brand.getbbox(short_brand)
    cw = cbox[2] - cbox[0]
    draw.text((cx - cw // 2 - cbox[0], cy + 120), short_brand, font=font_card_brand, fill=(255, 255, 255, 255))

    font_tier = get_font(FONT_BOLD, 17)
    draw_pill(draw, (cx - 85, cy + 180), "OFFICIAL LICENSE", font_tier, bg_color=(16, 185, 129, 65), text_color=(52, 211, 153), pad_x=16, pad_y=6, radius=16)

    out_path = os.path.join(MEDIA_PROD_DIR, filename)
    final_img = img.convert("RGB")
    final_img.save(out_path, quality=94, optimize=True)
    return f"products/{filename}"


# Define the products to seed
PRODUCTS_DATA = [
    {
        "name": "ChatGPT Plus",
        "category": "AI Tools",
        "badge": "Top Seller",
        "subtitle": "Unleash GPT-4o, o1-preview, and advanced AI Canvas",
        "icon": "🤖",
        "filename": "chatgpt_plus.jpg",
        "colors": {
            "bg1": (10, 24, 20),
            "bg2": (13, 40, 32),
            "accent": (16, 185, 129) # Emerald
        },
        "features": [
            "Access to GPT-4o & o1 Advanced Reasoning",
            "DALL-E 3 High-Res Image Generation",
            "Advanced Voice Mode with real-time audio",
            "Custom GPTs & Python Data Analysis"
        ],
        "description": {
            "en": "Supercharge your productivity, writing, and coding with ChatGPT Plus. Instant activation on shared or dedicated account profiles.",
            "bn": "চ্যাটজিপিটি প্লাস সাবস্ক্রিপশন নিয়ে আপনার প্রডাক্টিভিটি, কোডিং ও রাইটিংকে নিয়ে যান নতুন উচ্চতায়।"
        },
        "warranty": "Full replacement warranty for active subscription period.",
        "delivery": "Instant automated access delivery via Email within 5-15 mins.",
        "plans": [
            {"name": "1 Device Plan", "price": 450.00, "devices": 1, "billing_cycle": "monthly", "is_default": True},
            {"name": "2 Devices Plan", "price": 850.00, "devices": 2, "billing_cycle": "monthly", "is_default": False},
            {"name": "Private Full Account", "price": 2400.00, "devices": 1, "billing_cycle": "monthly", "is_default": False},
            {"name": "1 Year Pro Access", "price": 24000.00, "devices": 1, "billing_cycle": "yearly", "is_default": False},
        ]
    },
    {
        "name": "Netflix Premium 4K UHD",
        "category": "Streaming",
        "badge": "4K Ultra HD",
        "subtitle": "Stream in Ultra HD 4K, HDR, and Dolby Atmos audio",
        "icon": "🍿",
        "filename": "netflix_premium.jpg",
        "colors": {
            "bg1": (18, 12, 14),
            "bg2": (40, 10, 15),
            "accent": (229, 9, 20) # Netflix Red
        },
        "features": [
            "Ultra HD 4K + HDR & Dolby Vision Quality",
            "Spatial Audio for immersive theater sound",
            "Offline downloads on phone and tablet",
            "100% Ad-Free movies, series & anime"
        ],
        "description": {
            "en": "Unlimited entertainment with Netflix Premium Ultra HD. Enjoy on Smart TVs, smartphones, PCs, and gaming consoles.",
            "bn": "নেটফ্লিক্স প্রিমিয়াম ৪কে আল্ট্রা এইচডি সাবস্ক্রিপশন। টিভি, ফোন এবং পিসিতে বিজ্ঞাপনহীন মুভি ও সিরিজ উপভোগ করুন।"
        },
        "warranty": "30-day instant replacement warranty guarantee.",
        "delivery": "Instant profile login details sent via SMS & Email.",
        "plans": [
            {"name": "1 Screen (PIN Locked)", "price": 320.00, "devices": 1, "billing_cycle": "monthly", "is_default": True},
            {"name": "2 Screens Plan", "price": 600.00, "devices": 2, "billing_cycle": "monthly", "is_default": False},
            {"name": "4 Screens (Full Private)", "price": 1190.00, "devices": 4, "billing_cycle": "monthly", "is_default": False},
        ]
    },
    {
        "name": "Spotify Premium",
        "category": "Streaming",
        "badge": "Hi-Fi Audio",
        "subtitle": "Millions of songs and podcasts without any ad interruptions",
        "icon": "🎧",
        "filename": "spotify_premium.jpg",
        "colors": {
            "bg1": (12, 24, 18),
            "bg2": (10, 36, 22),
            "accent": (29, 185, 84) # Spotify Green
        },
        "features": [
            "Ad-Free music streaming with zero interruptions",
            "Offline downloads for listening on the go",
            "Unlimited track skips & playlist shuffling",
            "Very High Quality 320kbps audio bitrate"
        ],
        "description": {
            "en": "Experience seamless music listening across all your devices with Spotify Premium.",
            "bn": "স্পটিফাই প্রিমিয়াম সাবস্ক্রিপশন নিয়ে যেকোনো সময় যেকোনো গান শুনুন সম্পূর্ণ বিজ্ঞাপন ছাড়া।"
        },
        "warranty": "100% full duration replacement guarantee.",
        "delivery": "Direct invite delivered straight to your Spotify account.",
        "plans": [
            {"name": "1 Month Individual", "price": 190.00, "devices": 1, "billing_cycle": "monthly", "is_default": True},
            {"name": "3 Months Individual", "price": 520.00, "devices": 1, "billing_cycle": "quarterly", "is_default": False},
            {"name": "1 Year Pro Individual", "price": 1750.00, "devices": 1, "billing_cycle": "yearly", "is_default": False},
            {"name": "1 Year Family (6 Members)", "price": 2900.00, "devices": 6, "billing_cycle": "yearly", "is_default": False},
        ]
    },
    {
        "name": "Canva Pro",
        "category": "Design & Creative",
        "badge": "Pro Creative",
        "subtitle": "100M+ stock assets, Magic AI tools, and 1TB Cloud Storage",
        "icon": "🎨",
        "filename": "canva_pro.jpg",
        "colors": {
            "bg1": (22, 12, 36),
            "bg2": (40, 18, 65),
            "accent": (168, 85, 247) # Canva Purple
        },
        "features": [
            "100+ Million premium stock photos & videos",
            "1-Click Magic Background Remover",
            "Brand Kits, custom typography & logos",
            "Magic Resize and AI generative tools"
        ],
        "description": {
            "en": "Empower your graphic design, social media posts, and presentations with Canva Pro team access.",
            "bn": "ক্যানভা প্রো এক্সেস দিয়ে প্রফেশনাল গ্রাফিক ডিজাইন তৈরি করুন চোখের পলকে।"
        },
        "warranty": "Lifetime / Full validity replacement guarantee.",
        "delivery": "Instant invite delivered straight to your own email address.",
        "plans": [
            {"name": "1 Month Pro Access", "price": 160.00, "devices": 1, "billing_cycle": "monthly", "is_default": True},
            {"name": "6 Months Pro Access", "price": 490.00, "devices": 1, "billing_cycle": "biannual", "is_default": False},
            {"name": "1 Year Pro Access", "price": 790.00, "devices": 1, "billing_cycle": "yearly", "is_default": False},
            {"name": "Lifetime Team Member", "price": 1250.00, "devices": 1, "billing_cycle": "lifetime", "is_default": False},
        ]
    },
    {
        "name": "NordVPN Pro",
        "category": "Security & Privacy",
        "badge": "High Security",
        "subtitle": "6,400+ high-speed servers in 111 countries with No-Logs",
        "icon": "🛡️",
        "filename": "nordvpn_pro.jpg",
        "colors": {
            "bg1": (10, 18, 36),
            "bg2": (15, 30, 60),
            "accent": (59, 130, 246) # Cyber Blue
        },
        "features": [
            "6,400+ Ultra-fast servers across 111 countries",
            "Threat Protection against malware and trackers",
            "Strict independently audited No-Logs policy",
            "Kill Switch & Double VPN military encryption"
        ],
        "description": {
            "en": "Protect your digital privacy and browse without borders using NordVPN Pro.",
            "bn": "নর্ডভিপিএন প্রো এর মাধ্যমে সম্পূর্ণ নিরাপদ ও গোপনীয়তার সাথে ইন্টারনেট ব্যবহার করুন।"
        },
        "warranty": "100% money-back & full duration replacement warranty.",
        "delivery": "Instant automated license credentials delivered to your inbox.",
        "plans": [
            {"name": "1 Device (1 Month)", "price": 280.00, "devices": 1, "billing_cycle": "monthly", "is_default": True},
            {"name": "2 Devices (6 Months)", "price": 990.00, "devices": 2, "billing_cycle": "biannual", "is_default": False},
            {"name": "6 Devices (1 Year Pro)", "price": 1850.00, "devices": 6, "billing_cycle": "yearly", "is_default": False},
            {"name": "6 Devices (2 Years Ultra)", "price": 3200.00, "devices": 6, "billing_cycle": "custom", "is_default": False},
        ]
    },
    {
        "name": "YouTube Premium",
        "category": "Streaming",
        "badge": "Ad-Free Video",
        "subtitle": "Ad-free playback, mobile background play, and YouTube Music",
        "icon": "▶️",
        "filename": "youtube_premium.jpg",
        "colors": {
            "bg1": (22, 10, 12),
            "bg2": (42, 14, 18),
            "accent": (244, 63, 94) # Rose / Red
        },
        "features": [
            "Completely Ad-Free YouTube video streaming",
            "Background playback while using other apps",
            "Offline video downloads on smartphone/tablet",
            "Includes full YouTube Music Premium access"
        ],
        "description": {
            "en": "Upgrade your YouTube experience with zero ads, background play, and YouTube Music included.",
            "bn": "ইউটিউব প্রিমিয়াম নিয়ে বিজ্ঞাপনহীন ভিডিও এবং ব্যাকগ্রাউন্ড মিউজিক উপভোগ করুন।"
        },
        "warranty": "Full subscription validity replacement guarantee.",
        "delivery": "Direct Google Family invite delivered to your Gmail.",
        "plans": [
            {"name": "1 Month Individual", "price": 130.00, "devices": 1, "billing_cycle": "monthly", "is_default": True},
            {"name": "6 Months Member", "price": 690.00, "devices": 1, "billing_cycle": "biannual", "is_default": False},
            {"name": "1 Year Member", "price": 1250.00, "devices": 1, "billing_cycle": "yearly", "is_default": False},
        ]
    }
]

def seed_database():
    admin_user = User.objects.filter(is_superuser=True).first()
    
    # Also update Gemini AI (ID: 2) banner and clean up plans
    try:
        gemini = Product.objects.get(id=2)
        gemini_banner = generate_banner(
            "gemini_advanced.jpg", "Google Gemini Pro", "Next-generation multimodal reasoning and Google One 2TB",
            "Google AI", {"bg1": (12, 15, 32), "bg2": (22, 28, 60), "accent": (66, 133, 244)}, "✨",
            [
                "Gemini 1.5 Pro with 1M token context",
                "Integrated with Gmail, Docs and Drive",
                "Includes 2TB Google One Cloud Storage",
                "Advanced Python code execution"
            ]
        )
        gemini.name = "Google Gemini Advanced"
        gemini.image = gemini_banner
        gemini.features = [
            "Gemini 1.5 Pro with 1M token context window",
            "Includes 2TB Google One Cloud Storage",
            "Deep integration with Gmail, Docs and Drive",
            "Advanced Python coding & multimodal analysis"
        ]
        gemini.warranty = "Full duration replacement warranty."
        gemini.delivery = "Instant invitation sent to your Google Account."
        gemini.save()
        
        # Clean duplicate plans for Gemini
        gemini.plans.all().delete()
        p1 = ProductPlan.objects.create(product=gemini, name="1 Device Plan", price=350.00, devices=1, billing_cycle="monthly", is_default=True)
        p2 = ProductPlan.objects.create(product=gemini, name="2 Devices Plan", price=650.00, devices=2, billing_cycle="monthly", is_default=False)
        p3 = ProductPlan.objects.create(product=gemini, name="5 Devices Plan", price=1200.00, devices=5, billing_cycle="monthly", is_default=False)
        gemini.selected_plan = p1
        gemini.save()
        print("Updated Google Gemini Advanced (ID: 2) successfully!")
    except Product.DoesNotExist:
        pass

    for item in PRODUCTS_DATA:
        # 1. Category
        cat, _ = Category.objects.get_or_create(name=item["category"])
        
        # 2. Banner Image
        banner_rel_path = generate_banner(
            item["filename"],
            item["name"],
            item["subtitle"],
            item["badge"],
            item["colors"],
            item["icon"],
            item["features"]
        )

        # 3. Product
        product, created = Product.objects.get_or_create(
            name=item["name"],
            defaults={
                "category": cat,
                "image": banner_rel_path,
                "features": item["features"],
                "description": item["description"],
                "warranty": item["warranty"],
                "delivery": item["delivery"],
                "is_active": True,
                "created_by": admin_user,
            }
        )

        if not created:
            product.category = cat
            product.image = banner_rel_path
            product.features = item["features"]
            product.description = item["description"]
            product.warranty = item["warranty"]
            product.delivery = item["delivery"]
            product.is_active = True
            product.save()

        # 4. Plans
        product.plans.all().delete()
        default_plan = None
        for plan_info in item["plans"]:
            pl = ProductPlan.objects.create(
                product=product,
                name=plan_info["name"],
                price=plan_info["price"],
                currency="BDT",
                devices=plan_info["devices"],
                billing_cycle=plan_info["billing_cycle"],
                is_default=plan_info["is_default"],
                is_active=True
            )
            if plan_info["is_default"]:
                default_plan = pl

        product.selected_plan = default_plan or product.plans.first()
        product.save()
        print(f"Product '{product.name}' (ID: {product.id}) saved with {product.plans.count()} plans.")

if __name__ == "__main__":
    seed_database()
    print("Database seeding completed successfully!")
