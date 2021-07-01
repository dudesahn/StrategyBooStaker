import pytest
from brownie import config, Wei, Contract

# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Define relevant tokens and contracts in this section
@pytest.fixture(scope="module")
def token():
    # this should be the address of the ERC-20 used by the strategy/vault. In this case, SUSHI
    token_address = "0x6B3595068778DD592e39A122f4f5a5cF09C90fE2"
    yield Contract(token_address)

@pytest.fixture(scope="module")
def healthCheck():
    yield Contract('0xDDCea799fF1699e98EDF118e0629A974Df7DF012')

@pytest.fixture(scope="module")
def xyz():
    yield Contract("0x618679dF9EfCd19694BB1daa8D00718Eacfa2883")


@pytest.fixture(scope="module")
def rewardscontract():
    yield Contract("0xe3e1860a5653c030818226e0cB1efb4a477A5F32")


@pytest.fixture(scope="module")
def staking():
    yield Contract("0x2d615795a8bdb804541C69798F13331126BA0c09")


# Define any accounts in this section
@pytest.fixture(scope="module")
def gov(accounts):
    # yearn multis... I mean YFI governance. I swear!
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)


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
def whale(accounts):
    # Totally in it for the tech (largest EOA holder of SUSHI, binance wallet)
    whale = accounts.at("0x28C6c06298d514Db089934071355E5743bf21d60", force=True)
    yield whale


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
    StrategyUniverseStaking,
    gov,
    guardian,
    rewardscontract,
    whale,
    token,
    chain,
    healthCheck,
):
    # parameters for this are: strategy, vault, max deposit, minTimePerInvest, slippage protection (10000 = 100% slippage allowed),
    strategy = guardian.deploy(StrategyUniverseStaking, vault, rewardscontract)
    strategy.setKeeper(keeper, {"from": gov})
    vault.setManagementFee(0, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    strategy.setStrategist(strategist, {"from": gov})
    strategy.setHealthCheck(healthCheck, {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})
    chain.sleep(1)
    yield strategy
