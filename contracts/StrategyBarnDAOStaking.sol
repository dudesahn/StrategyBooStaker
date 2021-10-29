// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

// These are the core Yearn libraries
import {
    BaseStrategy,
    StrategyParams
} from "@yearnvaults/contracts/BaseStrategy.sol";
import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "@openzeppelin/contracts/math/Math.sol";

interface IBaseFee {
    function basefee_global() external view returns (uint256);
}

interface IUniV3 {
    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }

    function exactInput(ExactInputParams calldata params)
        external
        payable
        returns (uint256 amountOut);
}

interface IUniswapV2Router02 {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);

    function getAmountsOut(uint256 amountIn, address[] calldata path)
        external
        view
        returns (uint256[] memory amounts);
}

interface IStaking {
    function deposit(address tokenAddress, uint256 amount) external; // pass want as tokenAdress here

    function withdraw(address tokenAddress, uint256 amount) external; // pass want as tokenAdress here

    function emergencyWithdraw(address tokenAddress) external; // can only be done if the last withdraw was > 10 epochs before

    function balanceOf(address user, address token)
        external
        view
        returns (uint256); // how much of our want we have staked
}

interface IFarming {
    function massHarvest() external returns (uint256); // this is claiming our rewards
}

contract StrategyBarnDAOStaking is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    /* ========== STATE VARIABLES ========== */

    address public staking; // DAO staking contract
    address public farmingContract; // This is the rewards contract we claim from
    IERC20 public emissionToken; // this is the token we receive from staking

    uint256 public sellCounter; // track our sells
    uint256 public sellsPerEpoch; // number of sells we divide our claim up into

    // swap stuff
    address public constant uniswapv3 =
        0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address public constant sushiswapRouter =
        0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F;
    bool public sellOnSushi; // determine if we sell partially on sushi or all on Uni v3
    uint24 public uniWantFee; // this is equal to 0.3%, can change this later if a different path becomes more optimal
    uint256 public maxGasPrice; // this is the max gas price we want our keepers to pay for harvests/tends in gwei

    IERC20 public constant usdc =
        IERC20(0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48);
    IERC20 public constant weth =
        IERC20(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);

    string internal stratName; // we use this to be able to adjust our strategy's name
    bool internal isOriginal = true;

    /* ========== CONSTRUCTOR ========== */

    constructor(
        address _vault,
        address _farmingContract,
        address _emissionToken,
        address _staking,
        string memory _name
    ) public BaseStrategy(_vault) {
        _initializeStrat(_farmingContract, _emissionToken, _staking, _name);
    }

    /* ========== CLONING ========== */

    event Cloned(address indexed clone);

    // we use this to clone our original strategy to other vaults
    function cloneBarnDAOStrategy(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _farmingContract,
        address _emissionToken,
        address _staking,
        string memory _name
    ) external returns (address newStrategy) {
        require(isOriginal);
        // Copied from https://github.com/optionality/clone-factory/blob/master/contracts/CloneFactory.sol
        bytes20 addressBytes = bytes20(address(this));
        assembly {
            // EIP-1167 bytecode
            let clone_code := mload(0x40)
            mstore(
                clone_code,
                0x3d602d80600a3d3981f3363d3d373d3d3d363d73000000000000000000000000
            )
            mstore(add(clone_code, 0x14), addressBytes)
            mstore(
                add(clone_code, 0x28),
                0x5af43d82803e903d91602b57fd5bf30000000000000000000000000000000000
            )
            newStrategy := create(0, clone_code, 0x37)
        }

        StrategyBarnDAOStaking(newStrategy).initialize(
            _vault,
            _strategist,
            _rewards,
            _keeper,
            _farmingContract,
            _emissionToken,
            _staking,
            _name
        );

        emit Cloned(newStrategy);
    }

    // this will only be called by the clone function above
    function initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _farmingContract,
        address _emissionToken,
        address _staking,
        string memory _name
    ) public {
        _initialize(_vault, _strategist, _rewards, _keeper);
        _initializeStrat(_farmingContract, _emissionToken, _staking, _name);
    }

    // this is called by our original strategy, as well as any clones
    function _initializeStrat(
        address _farmingContract,
        address _emissionToken,
        address _staking,
        string memory _name
    ) internal {
        // initialize variables
        minReportDelay = 0;
        maxReportDelay = 604800; // 7 days in seconds, if we hit this then harvestTrigger = True
        profitFactor = 1_000_000;
        debtThreshold = 1e18; // we shouldn't ever have debt, but set a bit of a buffer
        farmingContract = _farmingContract;
        sellsPerEpoch = 1;
        healthCheck = address(0xDDCea799fF1699e98EDF118e0629A974Df7DF012); // health.ychad.eth
        emissionToken = IERC20(_emissionToken);
        staking = _staking;

        // set our strategy's name
        stratName = _name;

        // start off using sushi
        sellOnSushi = true;

        // set our swap fee for univ3
        uniWantFee = 3000;

        // want is what we stake for emissions
        want.approve(address(staking), type(uint256).max);

        // add approvals on all tokens
        emissionToken.approve(sushiswapRouter, type(uint256).max);
        weth.approve(sushiswapRouter, type(uint256).max);
        usdc.approve(uniswapv3, type(uint256).max);

        // set our max gas price
        maxGasPrice = 100 * 1e9;
    }

    /* ========== VIEWS ========== */

    function name() external view override returns (string memory) {
        return stratName;
    }

    function balanceOfWant() public view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function balanceOfStaked() public view returns (uint256) {
        return IStaking(staking).balanceOf(address(this), address(want));
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        // look at our staked tokens and any free tokens sitting in the strategy
        return balanceOfStaked().add(balanceOfWant());
    }

    /* ========== MUTATIVE FUNCTIONS ========== */

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // claim our rewards
        if (sellCounter == 0) IFarming(farmingContract).massHarvest();

        // if we have emissionToken to sell, then sell some of it
        uint256 _emissionTokenBalance = emissionToken.balanceOf(address(this));
        if (_emissionTokenBalance > 0) {
            // sell some fraction of our rewards to avoid hitting too much slippage
            uint256 _toSell =
                _emissionTokenBalance.div(sellsPerEpoch.sub(sellCounter));

            // sell our emissionToken
            if (_toSell > 0) {
                if (sellOnSushi) {
                    // well sell mostly on Sushi
                    _sellMostlyOnSushi(_toSell);
                } else {
                    _sellMostlyOnUni(_toSell);
                }

                sellCounter = sellCounter.add(1);
                if (sellCounter == sellsPerEpoch) sellCounter = 0;
            }
        }

        // debtOustanding will only be > 0 in the event of revoking or lowering debtRatio of a strategy
        if (_debtOutstanding > 0) {
            // add in a check for > 0 as withdraw reverts with 0 amount
            if (balanceOfStaked() > 0) {
                IStaking(staking).withdraw(
                    address(want),
                    Math.min(balanceOfStaked(), _debtOutstanding)
                );
            }
            uint256 _withdrawnBal = balanceOfWant();
            _debtPayment = Math.min(_debtOutstanding, _withdrawnBal);
        }

        // serious loss should never happen, but if it does (for instance, if Curve is hacked), let's record it accurately
        uint256 assets = estimatedTotalAssets();
        uint256 debt = vault.strategies(address(this)).totalDebt;

        // if assets are greater than debt, things are working great!
        if (assets > debt) {
            _profit = assets.sub(debt);
            uint256 _wantBal = balanceOfWant();
            if (_profit.add(_debtPayment) > _wantBal) {
                // this should only be hit following donations to strategy
                liquidateAllPositions();
            }
        }
        // if assets are less than debt, we are in trouble
        else {
            _loss = debt.sub(assets);
        }
    }

    // sell from want to USDC via sushi, USDC -> WETH via Uni, WETH -> want via Uni
    function _sellMostlyOnUni(uint256 _amount) internal {
        // sell our emission token for USDC on sushi
        address[] memory emissionTokenPath = new address[](2);
        emissionTokenPath[0] = address(emissionToken);
        emissionTokenPath[1] = address(usdc);

        IUniswapV2Router02(sushiswapRouter).swapExactTokensForTokens(
            _amount,
            uint256(0),
            emissionTokenPath,
            address(this),
            block.timestamp
        );

        // sell our USDC for want through WETH on Uni
        uint256 _usdcBalance = usdc.balanceOf(address(this));
        IUniV3(uniswapv3).exactInput(
            IUniV3.ExactInputParams(
                abi.encodePacked(
                    address(usdc),
                    uint24(500),
                    address(weth),
                    uint24(uniWantFee),
                    address(want)
                ),
                address(this),
                block.timestamp,
                _usdcBalance,
                uint256(1)
            )
        );
    }

    // sell from want to USDC via sushi, USDC -> WETH via Uni, WETH -> want via Sushi
    function _sellMostlyOnSushi(uint256 _amount) internal {
        // sell our emission token for USDC on sushi
        address[] memory emissionTokenPath = new address[](2);
        emissionTokenPath[0] = address(emissionToken);
        emissionTokenPath[1] = address(usdc);

        IUniswapV2Router02(sushiswapRouter).swapExactTokensForTokens(
            _amount,
            uint256(0),
            emissionTokenPath,
            address(this),
            block.timestamp
        );

        // sell our usdc for weth on uni
        uint256 _usdcBalance = usdc.balanceOf(address(this));
        IUniV3(uniswapv3).exactInput(
            IUniV3.ExactInputParams(
                abi.encodePacked(address(usdc), uint24(500), address(weth)),
                address(this),
                block.timestamp,
                _usdcBalance,
                uint256(1)
            )
        );

        // sell our weth for want on sushi
        uint256 _wethBalance = weth.balanceOf(address(this));
        address[] memory wantTokenPath = new address[](2);
        wantTokenPath[0] = address(weth);
        wantTokenPath[1] = address(want);

        IUniswapV2Router02(sushiswapRouter).swapExactTokensForTokens(
            _wethBalance,
            uint256(0),
            wantTokenPath,
            address(this),
            block.timestamp
        );
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }
        // send all of our want tokens to be deposited
        uint256 _toInvest = balanceOfWant();
        // stake only if we have something to stake
        if (_toInvest > 0) {
            IStaking(staking).deposit(address(want), _toInvest);
        }
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 _wantBal = balanceOfWant();
        if (_amountNeeded > _wantBal) {
            uint256 _stakedBal = balanceOfStaked();
            // add in a check for > 0 as withdraw reverts with 0 amount
            if (_stakedBal > 0) {
                IStaking(staking).withdraw(
                    address(want),
                    Math.min(_stakedBal, _amountNeeded.sub(_wantBal))
                );
            }

            uint256 _withdrawnBal = balanceOfWant();
            _liquidatedAmount = Math.min(_amountNeeded, _withdrawnBal);
            _loss = _amountNeeded.sub(_liquidatedAmount);
        } else {
            // we have enough balance to cover the liquidation available
            return (_amountNeeded, 0);
        }
    }

    function liquidateAllPositions() internal override returns (uint256) {
        uint256 _stakedBal = balanceOfStaked();
        if (_stakedBal > 0) {
            IStaking(staking).withdraw(address(want), _stakedBal);
        }
        return balanceOfWant();
    }

    // only do this if absolutely necessary; as rewards won't be claimed, and this also must be 10 weeks after our last withdrawal. this will revert if we don't have anything to withdraw.
    function emergencyWithdraw() external onlyEmergencyAuthorized {
        IStaking(staking).emergencyWithdraw(address(want));
    }

    function prepareMigration(address _newStrategy) internal override {
        uint256 _stakedBal = balanceOfStaked();
        if (_stakedBal > 0) {
            IStaking(staking).withdraw(address(want), _stakedBal);
        }

        // send our claimed emissionToken to the new strategy
        emissionToken.safeTransfer(
            _newStrategy,
            emissionToken.balanceOf(address(this))
        );
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {}

    // our main trigger is regarding our DCA since there is low liquidity for our emissionToken
    function harvestTrigger(uint256 callCostinEth)
        public
        view
        override
        returns (bool)
    {
        // Should not trigger if strategy is not active (no assets and no debtRatio). This means we don't need to adjust keeper job.
        if (!isActive()) return false;

        // check if the base fee gas price is higher than we allow
        if (readBaseFee() > maxGasPrice) {
            return false;
        }

        return super.harvestTrigger(callCostinEth);
    }

    function ethToWant(uint256 _amtInWei)
        public
        view
        override
        returns (uint256)
    {
        uint256 _ethToWant;
        if (_amtInWei > 0) {
            address[] memory ethPath = new address[](2);
            ethPath[0] = address(weth);
            ethPath[1] = address(want);

            uint256[] memory callCostInWant =
                IUniswapV2Router02(sushiswapRouter).getAmountsOut(
                    _amtInWei,
                    ethPath
                );

            _ethToWant = callCostInWant[callCostInWant.length - 1];
        }
        return _ethToWant;
    }

    function readBaseFee() internal view returns (uint256 baseFee) {
        IBaseFee _baseFeeOracle =
            IBaseFee(0xf8d0Ec04e94296773cE20eFbeeA82e76220cD549);
        return _baseFeeOracle.basefee_global();
    }

    /* ========== SETTERS ========== */

    // set number of batches we sell our claimed emissionToken in
    function setSellsPerEpoch(uint256 _sellsPerEpoch)
        external
        onlyEmergencyAuthorized
    {
        require(
            15 > _sellsPerEpoch && _sellsPerEpoch > 0,
            "Must be above 0 and less than 15"
        );
        sellsPerEpoch = _sellsPerEpoch;
        // reset our counter to be safe
        sellCounter = 0;
    }

    // set the maximum gas price we want to pay for a harvest/tend in gwei
    function setGasPrice(uint256 _maxGasPrice) external onlyAuthorized {
        maxGasPrice = _maxGasPrice.mul(1e9);
    }

    // set the fee pool we'd like to swap through for if we're swapping from ETH to want on UniV3
    function setUniWantFee(uint24 _fee) external onlyAuthorized {
        uniWantFee = _fee;
    }

    // set if we want to sell our swap partly on sushi or just uniV3
    function setSellOnSushi(bool _sellOnSushi) external onlyAuthorized {
        sellOnSushi = _sellOnSushi;
    }
}
