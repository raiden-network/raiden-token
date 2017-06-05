# raiden-token
Raiden Token and Issuance Contracts

Setup:
- Deploy Mint (references Auction and Token)
- Deploy Auction (references Mint)
- Deploy Token(Mint)
- Mint.setup(Token, Auction)
- Auction.setup(Mint)

Basic flow:
 - Deploy Contracts with params, prealloc (if any)
 - Register eligible Bidders with Auction (Whitelist)
 - Start Auction
  - initial high minting period is reduced over time
  - bidders send bids (with ETH as collateral) if they agree with the current minting period
  - auction ends if maxCollateral is collected
 - At Auction End
  - Collateral is sent to Token via Mint
  - last minting period is the minting period for all successful bidders
- for successful bidders 
  - their minting right are registered with the Mint
  - which allows them to mint tokens proportional to the collateral they provided 
- minting rights allow to mint tokens over time
