import pytest
from brownie import config, Wei, Contract

# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Define relevant tokens and contracts in this section
@pytest.fixture(scope="module")
def token():  # this should be the address of the ERC-20 used by the strategy/vault. In this case, SUSHI
    token_address = "0x6B3595068778DD592e39A122f4f5a5cF09C90fE2"
    yield Contract(token_address)
    # SUSHI 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2
    # LINK 0x514910771AF9Ca656af840dff83E8264EcF986CA
    # SNX 0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F
    # XYZ 0x618679dF9EfCd19694BB1daa8D00718Eacfa2883
    # ILV 0x767FE9EDC9E0dF98E07454847909b5E959D7ca0E
    # BOND 0x0391D2021f89DC339F60Fff84546EA23E337750f
    # MANA 0x0F5D2fB29fb7d3CFeE444a200298f468908cC942


@pytest.fixture(scope="module")
def emissionToken():  # this is the token we receive to sell for more want
    yield Contract("0xd779eEA9936B4e323cDdff2529eb6F13d0A4d66e")
    # league 0x7b39917f9562C8Bc83c7a6c2950FF571375D505D
    # enter 0xd779eEA9936B4e323cDdff2529eb6F13d0A4d66e


@pytest.fixture(scope="module")
def rewardscontract():  # this is the individual farming contract for our want
    yield Contract("0xA9B4B5e05EF90cFb8644591186AbCf883eDA5735")
    # league
    # sushi 0xcCB04b5AD3eE27a1c3fe8eA15CaC802aD4F4f5B8
    # ilv 0x0636aAdbcfC05cEfAb81E80c5E5a1f49de2053A8
    # link 0xBc1ce49430073A3154beCd8A090E74845Cd835fC
    # snx 0xd4E9821F54cAf6019500252F88158f4D8f469922
    # sushi 0xcCB04b5AD3eE27a1c3fe8eA15CaC802aD4F4f5B8
    # bond 0x0Ee09C6F99b2D27D8Ca712033370647F347E32ba
    # xyz 0x11CF7938CDF238c70b406E4650CFfF40614107EE

    # enter
    # sushi 0xA9B4B5e05EF90cFb8644591186AbCf883eDA5735
    # hidden snx 0xfCeD219D83dFf48ee702dab93122de8d2aff314f
    # axs 0xEa0B66eEc998Bb559fA6f1c6b159828F0a2db09d
    # ilv 0x271DBa83ccADd6A9719e314F53D9BF4e2C79d21A
    # xyz 0xcBA851105bFa485E390FBD456B9190824aE1212a
    # mana 0x9b11E10f54010A52DdFAAF2E37C11EF9891a59F0
    # bond 0xd65483B8755aC5Fea7120e3f68Df961d88181Dd2


@pytest.fixture(scope="module")
def staking():  # this is the staking contract, will be the same for each pool in the same protocol
    yield Contract("0x3F148612315AaE2514AC630D6FAf0D94B8Cd8E33")
    # leagueDAO 0x43921eb2E5C78D9e887d3Ecd4620a3Bd606f4F95
    # enterDAO 0x3F148612315AaE2514AC630D6FAf0D94B8Cd8E33


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance. Make sure to do no more than half of their balance.
@pytest.fixture(scope="module")
def amount():
    amount = 20_000e18
    yield amount


# this is the name we want to give our strategy
@pytest.fixture(scope="module")
def strategy_name():
    strategy_name = "StrategyEnterSUSHI"
    yield strategy_name


############################################ ONLY ADJUST THINGS ABOVE HERE ############################################


@pytest.fixture(scope="module")
def whale(accounts):
    # Totally in it for the tech (largest EOA holder of SUSHI, binance wallet)
    whale = accounts.at("0x28C6c06298d514Db089934071355E5743bf21d60", force=True)
    yield whale


# Constants for testing

# for live testing, governance is the strategist MS; we will update this before we endorse
@pytest.fixture(scope="module")
def gov(accounts):
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)


@pytest.fixture(scope="module")
def dudesahn(accounts):
    yield accounts.at("0x8Ef63b525fceF7f8662D98F77f5C9A86ae7dFE09", force=True)


@pytest.fixture(scope="module")
def strategist_ms(accounts):
    # like governance, but better
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)


@pytest.fixture(scope="module")
def keeper(accounts):
    yield accounts.at("0x8Ef63b525fceF7f8662D98F77f5C9A86ae7dFE09", force=True)


@pytest.fixture(scope="module")
def rewards(accounts):
    yield accounts.at("0x8Ef63b525fceF7f8662D98F77f5C9A86ae7dFE09", force=True)


@pytest.fixture(scope="module")
def guardian(accounts):
    yield accounts[2]


@pytest.fixture(scope="module")
def management(accounts):
    yield accounts[3]


@pytest.fixture(scope="module")
def strategist(accounts):
    yield accounts.at("0x8Ef63b525fceF7f8662D98F77f5C9A86ae7dFE09", force=True)


@pytest.fixture(scope="module")
def healthCheck():
    yield Contract("0xDDCea799fF1699e98EDF118e0629A974Df7DF012")


@pytest.fixture(scope="module")
def other_vault_strategy():
    yield Contract("0x8423590CD0343c4E18d35aA780DF50a5751bebae")


# @pytest.fixture(scope="function")
# def vault(pm, gov, rewards, guardian, management, token, chain):
#     vault = Contract("0x497590d2d57f05cf8B42A36062fA53eBAe283498")
#     yield vault
#
#
# @pytest.fixture(scope="function")
# def strategy(
#     strategist,
#     keeper,
#     vault,
#     StrategyDAOStaking,
#     gov,
#     guardian,
#     rewardscontract,
#     whale,
#     token,
#     chain,
#     healthCheck,
# ):
#     # parameters for this are: strategy, vault, max deposit, minTimePerInvest, slippage protection (10000 = 100% slippage allowed),
#     strategy = Contract("0xC1810aa7F733269C39D640f240555d0A4ebF4264")
#     yield strategy


@pytest.fixture(scope="function")
def vault(pm, gov, rewards, guardian, management, token, chain):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    chain.sleep(1)
    yield vault


@pytest.fixture(scope="function")
def strategy(
    strategist,
    keeper,
    vault,
    StrategyDAOStaking,
    gov,
    guardian,
    rewardscontract,
    whale,
    token,
    chain,
    healthCheck,
    staking,
    emissionToken,
    strategy_name,
):
    # parameters for this are: strategy, vault, max deposit, minTimePerInvest, slippage protection (10000 = 100% slippage allowed),
    strategy = guardian.deploy(
        StrategyDAOStaking,
        vault,
        rewardscontract,
        emissionToken,
        staking,
        strategy_name,
    )
    strategy.setKeeper(keeper, {"from": gov})
    vault.setManagementFee(0, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    strategy.setStrategist(strategist, {"from": gov})
    strategy.setHealthCheck(healthCheck, {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})
    chain.sleep(1)
    yield strategy


@pytest.fixture(scope="module")
def dummy_gas_oracle(strategist, dummyBasefee):
    dummy_gas_oracle = strategist.deploy(dummyBasefee)
    yield dummy_gas_oracle
