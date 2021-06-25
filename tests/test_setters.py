import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-05-20
def test_setters(gov, token, vault, new_address, chain, strategy, rewardsContract, strat_setup):

    strategy.setSellsPerEpoch(5, {"from": gov})
    assert strategy.sellsPerEpoch() == 5