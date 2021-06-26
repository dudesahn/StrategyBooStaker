import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_setters(gov, strategy, shared_setup):

    strategy.setSellsPerEpoch(5, {"from": gov})
    assert strategy.sellsPerEpoch() == 5