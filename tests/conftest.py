import pytest
from brownie import config, Wei, Contract

# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass

# Define relevant tokens and contracts in this section

@pytest.fixture
def token():
    # this should be the address of the ERC-20 used by the strategy/vault. In this case, SUSHI
    token_address = "0x6B3595068778DD592e39A122f4f5a5cF09C90fE2"
    yield Contract(token_address)

@pytest.fixture
def xyz():
    yield Contract("0x618679dF9EfCd19694BB1daa8D00718Eacfa2883")

@pytest.fixture
def rewardscontract():
    yield Contract("0xe3e1860a5653c030818226e0cB1efb4a477A5F32")

@pytest.fixture
def staking():
    yield Contract("0x2d615795a8bdb804541C69798F13331126BA0c09")

# Define any accounts in this section
@pytest.fixture
def gov(accounts):
    # yearn multis... I mean YFI governance. I swear!
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)

@pytest.fixture
def dudesahn(accounts):
    yield accounts.at("0x8Ef63b525fceF7f8662D98F77f5C9A86ae7dFE09", force=True)

@pytest.fixture
def strategist_ms(accounts):
    # like governance, but better
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

@pytest.fixture
def keeper(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts[3]


@pytest.fixture
def strategist(accounts):
    yield accounts[4]

@pytest.fixture
def whale(accounts):
    # Totally in it for the tech (largest EOA holder of SUSHI, binance wallet)
    whale = accounts.at('0x28C6c06298d514Db089934071355E5743bf21d60', force=True)
    yield whale

@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault
    
@pytest.fixture
def strategy(strategist, keeper, vault, StrategyUniverseStaking, gov, guardian, rewardscontract, whale, token):
	# parameters for this are: strategy, vault, max deposit, minTimePerInvest, slippage protection (10000 = 100% slippage allowed), 
    strategy = guardian.deploy(StrategyUniverseStaking, vault, rewardscontract)
    strategy.setKeeper(keeper, {"from": gov})
    vault.setManagementFee(0, {"from": gov})
    vault.addStrategy(strategy, 10000, 0, 2 ** 256 -1, 1000, {"from": gov})
    strategy.setStrategist('0x8Ef63b525fceF7f8662D98F77f5C9A86ae7dFE09', {"from": gov})
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    strategy.harvest({"from": gov})
    yield strategy
