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

contract StrategyUniverseStaking is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    /* ========== STATE VARIABLES ========== */

    address internal constant staking =
        0x2d615795a8bdb804541C69798F13331126BA0c09; // Universe's staking contract
    address public farmingContract; // This is the rewards contract we claim from

    uint256 public sellCounter; // track our sells
    uint256 public sellsPerEpoch = 1; // number of sells we divide our claim up into

    address internal constant sushiswapRouter =
        0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F;

    IERC20 internal constant xyz =
        IERC20(0x618679dF9EfCd19694BB1daa8D00718Eacfa2883);
    IERC20 internal constant usdc =
        IERC20(0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48);
    IERC20 internal constant weth =
        IERC20(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);

    /* ========== CONSTRUCTOR ========== */

    constructor(address _vault, address _farmingContract)
        public
        BaseStrategy(_vault)
    {
        // You can set these parameters on deployment to whatever you want
        minReportDelay = 0;
        maxReportDelay = 604800; // 7 days in seconds, if we hit this then harvestTrigger = True
        debtThreshold = 4000 * 1e18; // we shouldn't ever have debt, but set a bit of a buffer
        farmingContract = _farmingContract;

        // want is either SUSHI, AAVE, LINK, SNX, or COMP
        want.safeApprove(address(staking), type(uint256).max);

        // add approvals on all tokens
        xyz.safeApprove(sushiswapRouter, type(uint256).max);
    }

    /* ========== VIEWS ========== */

    function name() external view override returns (string memory) {
        return "StrategyUniverseStaking";
    }

    function _balanceOfWant() internal view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function _balanceOfStaked() internal view returns (uint256) {
        return IStaking(staking).balanceOf(address(this), address(want));
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        // look at our staked tokens and any free tokens sitting in the strategy
        return _balanceOfStaked().add(_balanceOfWant());
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

        // if we have xyz to sell, then sell some of it
        uint256 _xyzBalance = xyz.balanceOf(address(this));
        if (_xyzBalance > 0) {
            // sell some fraction of our rewards to avoid hitting too much slippage
            uint256 _toSell = _xyzBalance.div(sellsPerEpoch.sub(sellCounter));

            // sell our XYZ
            if (_toSell > 0) {
                // xyz token path
                address[] memory xyzPath = new address[](4);
                xyzPath[0] = address(xyz);
                xyzPath[1] = address(usdc);
                xyzPath[2] = address(weth);
                xyzPath[3] = address(want);

                // sell it
                IUniswapV2Router02(sushiswapRouter).swapExactTokensForTokens(
                    _toSell,
                    uint256(0),
                    xyzPath,
                    address(this),
                    now
                );
                sellCounter = sellCounter.add(1);
                if (sellCounter == sellsPerEpoch) sellCounter = 0;
            }
        }

        // serious loss should never happen, but if it does (for instance, if Curve is hacked), let's record it accurately
        uint256 assets = estimatedTotalAssets();
        uint256 debt = vault.strategies(address(this)).totalDebt;

        // if assets are greater than debt, things are working great! loss will be 0 by default
        if (assets > debt) {
            _profit = _balanceOfWant();
        } else {
            // if assets are less than debt, we are in trouble. profit will be 0 by default
            _loss = debt.sub(assets);
        }

        // debtOustanding will only be > 0 in the event of revoking or lowering debtRatio of a strategy
        if (_debtOutstanding > 0) {
            // add in a check for > 0 as withdraw reverts with 0 amount
            if (_balanceOfStaked() > 0)
                IStaking(staking).withdraw(
                    address(want),
                    Math.min(_balanceOfStaked(), _debtOutstanding)
                );

            _debtPayment = Math.min(_debtOutstanding, _balanceOfWant());
            if (_debtPayment < _debtOutstanding) _loss = _debtOutstanding.sub(_debtPayment);
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }
        // send all of our want tokens to be deposited
        uint256 _toInvest = _balanceOfWant();
        // stake only if we have something to stake
        if (_toInvest > 0) IStaking(staking).deposit(address(want), _toInvest);
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 wantBal = _balanceOfWant();
        if (_amountNeeded > wantBal) {
            // add in a check for > 0 as withdraw reverts with 0 amount
            if (_balanceOfStaked() > 0)
                IStaking(staking).withdraw(
                    address(want),
                    Math.min(_balanceOfStaked(), _amountNeeded - wantBal)
                );

            uint256 withdrawnBal = _balanceOfWant();
            _liquidatedAmount = Math.min(_amountNeeded, withdrawnBal);

            // if _amountNeeded > withdrawnBal, then we have an error
            if (_amountNeeded > withdrawnBal) {
                uint256 assets = estimatedTotalAssets();
                uint256 debt = vault.strategies(address(this)).totalDebt;
                if (debt > assets) _loss = debt.sub(assets);
            }
        } else {
            // we have enough balance to cover the liquidation available
            return (_amountNeeded, 0);
        }
    }

    function liquidateAllPositions() internal override returns (uint256) {
        if (_balanceOfStaked() > 0)
            IStaking(staking).withdraw(address(want), _balanceOfStaked());
        return _balanceOfWant();
    }

    // only do this if absolutely necessary; as rewards won't be claimed, and this also must be 10 weeks after our last withdrawal. this will revert if we don't have anything to withdraw.
    function emergencyWithdraw() external onlyEmergencyAuthorized {
        IStaking(staking).emergencyWithdraw(address(want));
    }

    function prepareMigration(address _newStrategy) internal override {
        if (_balanceOfStaked() > 0)
            IStaking(staking).withdraw(address(want), _balanceOfStaked());

        // send our claimed xyz to the new strategy
        xyz.safeTransfer(_newStrategy, xyz.balanceOf(address(this)));
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {
        address[] memory protected = new address[](1);
        protected[0] = address(xyz);

        return protected;
    }

    // our main trigger is regarding our DCA since there is low liquidity for $XYZ
    function harvestTrigger(uint256 callCostinEth)
        public
        view
        override
        returns (bool)
    {
        StrategyParams memory params = vault.strategies(address(this));

        // Should not trigger if Strategy is not activated
        if (params.activation == 0) return false;

        // Should not trigger if we haven't waited long enough since previous harvest
        if (block.timestamp.sub(params.lastReport) < minReportDelay)
            return false;

        // Should trigger if hasn't been called in a while
        if (block.timestamp.sub(params.lastReport) >= maxReportDelay)
            return true;

        // If some amount is owed, pay it back
        // NOTE: Since debt is based on deposits, it makes sense to guard against large
        //       changes to the value from triggering a harvest directly through user
        //       behavior. This should ensure reasonable resistance to manipulation
        //       from user-initiated withdrawals as the outstanding debt fluctuates.
        uint256 outstanding = vault.debtOutstanding();
        if (outstanding > debtThreshold) return true;

        // Check for profits and losses
        uint256 total = estimatedTotalAssets();
        // Trigger if we have a loss to report
        if (total.add(debtThreshold) < params.totalDebt) return true;

        // Trigger if it's been long enough since our last harvest based on our DCA schedule. each epoch is 1 week.
        uint256 week = 86400 * 7;
        if (block.timestamp.sub(params.lastReport) > week.div(sellsPerEpoch))
            return true;
    }

    function ethToWant(uint256 _amtInWei)
        public
        view
        override
        returns (uint256)
    {
        address[] memory ethPath = new address[](2);
        ethPath[0] = address(weth);
        ethPath[1] = address(want);

        uint256[] memory callCostInWant =
            IUniswapV2Router02(sushiswapRouter).getAmountsOut(
                _amtInWei,
                ethPath
            );

        uint256 _ethToWant = callCostInWant[callCostInWant.length - 1];

        return _ethToWant;
    }

    /* ========== SETTERS ========== */

    // set number of batches we sell our claimed XYZ in
    function setSellsPerEpoch(uint256 _sellsPerEpoch)
        external
        onlyEmergencyAuthorized
    {
        require(15 > _sellsPerEpoch && _sellsPerEpoch > 0, "Must be above 0 and less than 15");
        sellsPerEpoch = _sellsPerEpoch;
        // reset our counter to be safe
        sellCounter = 0;
    }
}
