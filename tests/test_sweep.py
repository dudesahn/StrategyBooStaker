import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_sweep(
    gov,
    token,
    vault,
    dudesahn,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
):

    ## deposit to the vault after approving
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # Strategy want token doesn't work
    startingWhale = token.balanceOf(whale)
    token.transfer(strategy.address, 1000e18, {"from": whale})
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with brownie.reverts("!want"):
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts("!shares"):
        strategy.sweep(vault.address, {"from": gov})
