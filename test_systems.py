import asyncio
from dotenv import load_dotenv
load_dotenv()

async def test():
    from management.session import get_session_summary
    from management.risk import get_risk_state
    from data.database import get_today_stats
    from broker.deriv import get_balance, connect

    print("Testing all systems...")

    # Test session
    session = get_session_summary()
    print(f"Session: {session['session']}")
    print(f"Trading allowed: {session['trading_allowed']}")
    print(f"Best pair: {session['best_pair']}")

    # Test balance
    connect()
    balance = get_balance()
    print(f"Balance: ${balance:.2f}")

    # Test database
    stats = get_today_stats()
    print(f"Trades today: {stats['total_trades']}")
    print(f"Win rate: {stats['win_rate']}%")

    # Test risk
    risk = get_risk_state()
    print(f"Risk state: {risk}")

    print("Done!")

asyncio.run(test())