from eth_account import Account

pk = "0xf129f162d47b86a287d8065b3587ea4c1f65784b5ef5a5e12fd612bd75cabf6b"
try:
    acct = Account.from_key(pk)
    print("DERIVED ADDRESS FROM PRIVATE KEY:", acct.address)
    print("MATCHES 0xD6277...?", acct.address.lower() == "0xD6277C501465CFc329D8dd429908769718aa49FA".lower())
except Exception as e:
    print("Error deriving:", e)
