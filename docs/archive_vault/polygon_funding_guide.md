# Polygon Hot Wallet Funding Guide

To officially execute live transfer payouts via the AI-BS backend, the server's Hot Wallet (`0xD6277C501465CFc329D8dd429908769718aa49FA`) must be funded on the **Polygon Mainnet**.

You need two specific assets:
1. **POL (formerly MATIC):** Used to pay network gas fees for every transaction.
2. **USDC (USD Coin):** The actual stablecoin currency that is sent as the payout.

Follow these exact steps to safely fund the wallet.

---

## Step 1: Acquire Funds on a Centralized Exchange
If you do not already have cryptocurrency, you must use a centralized exchange (like Coinbase, Crypto.com, Kraken, or Binance) that supports withdrawals directly to the Polygon network.

1. Log into your exchange of choice.
2. Ensure your account is funded with USD (fiat) or an equivalent trading currency.

## Step 2: Purchase POL (Gas Fees)
Polygon recently upgraded their native token ticker from MATIC to POL. Some exchanges may still list it as MATIC.
1. Navigate to the trading or "Buy" section of your exchange.
2. Search for **POL (Polygon Ecosystem Token)** or **MATIC (Polygon)**.
3. Purchase a small amount. **$5 to $10 USD** worth is more than enough to cover hundreds of automated payout transactions.

## Step 3: Purchase USDC (Payout Funds)
1. Search for **USDC (USD Coin)** on your exchange.
2. Purchase the amount of USDC you wish to use for the initial live transfer test (e.g., $15 or whatever you intend to pay out to the destination wallet).

> [!WARNING]  
> Do not purchase USDT (Tether) or any other stablecoin. The AI-BS smart contract logic is hardcoded to interact specifically with the USDC contract on Polygon (`0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`).

## Step 4: Withdraw POL to the Hot Wallet
1. Navigate to your exchange's **Withdraw** or **Send** page.
2. Select **POL** (or **MATIC**) as the asset to withdraw.
3. **CRITICAL SUB-STEP - SELECT THE CORRECT NETWORK:** You will be asked to choose a network. You MUST select **Polygon**. Do NOT select Ethereum (ERC-20), Cronos, or Binance Smart Chain. If you send it on the wrong network, the funds will not appear in the AI-BS treasury.
4. Enter the AI-BS Hot Wallet address exactly as follows:
   `0xD6277C501465CFc329D8dd429908769718aa49FA`
5. Enter the amount to withdraw (e.g., 5 POL) and confirm the transaction.

## Step 5: Withdraw USDC to the Hot Wallet
1. Start a new withdrawal and select **USDC** as the asset.
2. **CRITICAL SUB-STEP - SELECT THE CORRECT NETWORK:** Again, you MUST select the **Polygon** network for the withdrawal. Do NOT select Ethereum (ERC-20), Solana, or Base.
3. Enter the exact same AI-BS Hot Wallet address:
   `0xD6277C501465CFc329D8dd429908769718aa49FA`
4. Enter your payout test amount (e.g., 15 USDC) and confirm the transaction.

> [!CAUTION]  
> If it is your first time doing this, it is highly recommended to send a $1 test transaction of USDC first, verify it arrives on Polygonscan, and then send the remaining bulk.

## Step 6: Verify Funds in the AI-BS Matrix
Withdrawals from centralized exchanges to the Polygon network typically take 2 to 5 minutes to clear.

1. Open your browser and navigate to the Polygon network explorer for the hot wallet:
   [https://polygonscan.com/address/0xD6277C501465CFc329D8dd429908769718aa49FA](https://polygonscan.com/address/0xD6277C501465CFc329D8dd429908769718aa49FA)
2. Look at the "Token Holdings" dropdown on Polygonscan. You should see your USDC listed.
3. Check the internal AI-BS backend by running the Treasury Status API or viewing the System Economics Dashboard. You should see the `usdc_balance` and `pol_balance` update from `0.0`.

Once both balances reflect the deposited amounts, the `/v1/network/redeem-payout` API will automatically use the POL to pay gas and transfer the USDC to the destination wallet during the next live payout execution.
