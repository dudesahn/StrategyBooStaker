// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

// - harvest uses a "sell counter"
// - have this number be adjustable
// - sell 1 / (counterMax - counter) of our balance


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
import {IUniswapV2Router02} from "./interfaces/uniswap.sol";


interface IStaking {
    function deposit(address tokenAddress, uint256 amount) external; // pass want as tokenAdress here
    function withdraw(address tokenAddress, uint256 amount) external; // pass want as tokenAdress here
    function emergencyWithdraw(address tokenAddress) external; // can only be done if the last withdraw was > 10 epochs before
    function balanceOf(address user, address token) external view returns (uint256); // how much of our want we have staked
}

interface IRewards {
    function claim() external; // this is claiming our rewards
    function owed(address userAddress) external; // this is how much XYZ token we can claim
}

contract StrategyUniverseStaking is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
    
    /* ========== STATE VARIABLES ========== */

    address internal constant staking = 0x2d615795a8bdb804541C69798F13331126BA0c09; // Universe's staking contract
    address internal constant rewards = 0xF306Ad6a3E2aBd5CFD6687A2C86998f1d9c31205; // This is the rewards contract we claim from

    uint256 public sellCounter; // track our sells
    uint256 public sellsPerEpoch = 2; // number of sells we divide our claim up into

    IERC20 public constant xyz =
        IERC20(0x618679dF9EfCd19694BB1daa8D00718Eacfa2883);
    IERC20 public constant usdc =
        IERC20(0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48);
    IERC20 public constant weth =
        IERC20(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);


    /* ========== CONSTRUCTOR ========== */

    constructor(address _vault) public BaseStrategy(_vault) {
        // You can set these parameters on deployment to whatever you want
        minReportDelay = 0;
        maxReportDelay = 604800; // 7 days in seconds, if we hit this then harvestTrigger = True
        debtThreshold = 4000 * 1e18; // we shouldn't ever have debt, but set a bit of a buffer
        profitFactor = 4000; // in this strategy, profitFactor is only used for telling keep3rs when to move funds from vault to strategy (what previously was an earn call)

        // want = crvIB, Curve's Iron Bank pool (ycDai+ycUsdc+ycUsdt)
        want.safeApprove(address(staking), type(uint256).max);

        // add approvals on all tokens
        xyz.safeApprove(sushiswapRouter, type(uint256).max);

        // xyz token path
        xyzPath = new address[](4);
        xyzPath[0] = address(xyz);
        xyzPath[1] = address(usdc);
        xyzPath[2] = address(weth);
        xyzPath[3] = address(want);
    }

    /* ========== VIEWS ========== */

    function name() external view override returns (string memory) {
        return "StrategyUniverseStaking";
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        // look at our staked tokens and any free tokens sitting in the strategy
        return IStaking(staking).balanceOf(address(this), address(want)).add(want.balanceOf(address(this)));
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // if we have anything to claim, then claim our rewards
        uint256 owed = IRewards(rewards).owed(address(this));
        if (owed > 0) {
            // claim our rewards
            IRewards(rewards).claim();
        }
        
        // if we have xyz to sell, then sell some of it
        uint256 _xyzBalance = xyz.balanceOf(address(this));            
        if (_xyzBalance > 0) {
            // sell some fraction of our rewards to avoid hitting too much slippage
            uint256 _toSell = _xyzBalance.mul(1.div(sellsPerEpoch.sub(sellCounter)))
            
            // sell our XYZ
            if (_toSell > 0) IUniswapV2Router02(sushiswapRouter).swapExactTokensForTokens(_toSell, uint256(0), xyzPath, address(this), now);
            
        }

        // serious loss should never happen, but if it does (for instance, if Curve is hacked), let's record it accurately
        uint256 assets = estimatedTotalAssets();
        uint256 debt = vault.strategies(address(this)).totalDebt;

        // if assets are greater than debt, things are working great!
        if (assets > debt) {
            _profit = want.balanceOf(address(this));
        } else {
            // if assets are less than debt, we are in trouble
            _loss = debt.sub(assets);
            _profit = 0;
        }

        // debtOustanding will only be > 0 in the event of revoking or lowering debtRatio of a strategy
        if (_debtOutstanding > 0) {
        	uint256 stakedTokens = IStaking(staking).balanceOf(address(this), address(want));
        	IStaking(staking).withdraw(address(want), Math.min(stakedTokens, _debtOutstanding));

            _debtPayment = Math.min(
                _debtOutstanding,
                want.balanceOf(address(this))
            );
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }
        // send all of our want tokens to be deposited
        uint256 _toInvest = want.balanceOf(address(this));
        // stake only if we have something to stake
        if (_toInvest > 0) IStaking(staking).deposit(address(want), _toInvest);
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 wantBal = want.balanceOf(address(this));
        if (_amountNeeded > wantBal) {
        	uint256 stakedTokens = IStaking(staking).balanceOf(address(this), address(want));
        	IStaking(staking).withdraw(address(want), Math.min(stakedTokens, _amountNeeded - wantBal));

            uint256 withdrawnBal = want.balanceOf(address(this));
            _liquidatedAmount = Math.min(_amountNeeded, withdrawnBal);

            // if _amountNeeded != withdrawnBal, then we have an error
            if (_amountNeeded != withdrawnBal) {
                uint256 assets = estimatedTotalAssets();
                uint256 debt = vault.strategies(address(this)).totalDebt;
                _loss = debt.sub(assets);
            }
        } else {
          // we have enough balance to cover the liquidation available
          return (_amountNeeded, 0);
        }
    }

    function liquidateAllPositions() internal override returns (uint256) {
        uint256 stakedTokens = IStaking(staking).balanceOf(address(this), address(want));
        if (stakedTokens > 0) IStaking(staking).withdraw(address(want), stakedTokens);
        return want.balanceOf(address(this));
    }
    
    // only do this if absolutely necessary
    function emergencyWithdraw() external onlyAuthorized {
    	IStaking(staking).emergencyWithdraw(address(want));
    }

    // NOTE: Can override `tendTrigger` and `harvestTrigger` if necessary

    function prepareMigration(address _newStrategy) internal override {
    	// see how much we have staked and how much we can claim
        uint256 stakedTokens = IStaking(staking).balanceOf(address(this), address(want));
        uint256 owed = IRewards(rewards).owed(address(this));
        
        // claim rewards if we have them and withdraw our staked want tokens if we have them
        if (owed > 0) IRewards(rewards).claim();
        if (stakedTokens > 0) IStaking(staking).withdraw(address(want), stakedTokens);
        
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
    
    }

    function ethToWant(uint256 _amtInWei)
        public
        view
        virtual
        override
        returns (uint256)
    {
    	address[] memory ethPath = new address[](3);
        ethPath[0] = address(weth);
        ethPath[1] = address(usdc);
        ethPath[2] = address(xyz);

        uint256[] memory callCostInWant = IUniswapV2Router02(sushiswapRouter).getAmountsOut(_amtInWei, ethPath);

        uint256 _ethToWant = callCostInWant[callCostInDai.length - 1];
    
        return _ethToWant;
    }
    
    // set number of batches we sell our claimed XYZ in
    function setSellsPerEpoch(uint256 _sellsPerEpoch)
        external
        onlyAuthorized
    {
        sellsPerEpoch = _sellsPerEpoch;
    }
    
}
