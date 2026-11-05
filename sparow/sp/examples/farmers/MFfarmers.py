import random
import math
from munch import Munch
import pyomo.environ as pyo
from sparow.sp import stochastic_program

random.seed(923874938740938740)


#
# Global data for the HF model:
#
class GlobalData:
    num_plots = 20
    num_scens = 3  ### should be >= 3


if GlobalData.num_scens < 3:
    raise RuntimeError(f"Number of scenarios must be >= 3")

#
# list of possible per-plot scenarios for LF model:
#
LF_scendata = {
    "scenarios": [
        dict(
            ID="scen_0",
            data={"Yield": {"WHEAT": 2.0, "CORN": 2.4, "SUGAR_BEETS": 16.0}},
            probability=0.3,
        ),
        dict(
            ID="scen_1",
            data={"Yield": {"WHEAT": 2.5, "CORN": 3.0, "SUGAR_BEETS": 20.0}},
            probability=0.3,
        ),
        dict(
            ID="scen_2",
            data={"Yield": {"WHEAT": 3.0, "CORN": 3.6, "SUGAR_BEETS": 24.0}},
            probability=0.4,
        ),
    ]
}

#
# list of possible per-plot scenarios for HF model:
#
HF_scendata = {
    "scenarios": [
        dict(
            ID="BBB",
            data={"Yield": {"WHEAT": 2.0, "CORN": 2.4, "SUGAR_BEETS": 16.0}},
            probability=0.027,
        ),
        dict(
            ID="VVV",
            data={"Yield": {"WHEAT": 2.5, "CORN": 3.0, "SUGAR_BEETS": 20.0}},
            probability=0.027,
        ),
        dict(
            ID="AAA",
            data={"Yield": {"WHEAT": 3.0, "CORN": 3.6, "SUGAR_BEETS": 24.0}},
            probability=0.064,
        ),
        dict(
            ID="BBV",
            data={"Yield": {"WHEAT": 2.0, "CORN": 2.4, "SUGAR_BEETS": 20.0}},
            probability=0.027,
        ),
        dict(
            ID="BBA",
            data={"Yield": {"WHEAT": 2.0, "CORN": 2.4, "SUGAR_BEETS": 24.0}},
            probability=0.036,
        ),
        dict(
            ID="BVB",
            data={"Yield": {"WHEAT": 2.0, "CORN": 3.0, "SUGAR_BEETS": 16.0}},
            probability=0.027,
        ),
        dict(
            ID="BAB",
            data={"Yield": {"WHEAT": 2.0, "CORN": 3.6, "SUGAR_BEETS": 16.0}},
            probability=0.036,
        ),
        dict(
            ID="VBB",
            data={"Yield": {"WHEAT": 2.5, "CORN": 2.4, "SUGAR_BEETS": 16.0}},
            probability=0.027,
        ),
        dict(
            ID="ABB",
            data={"Yield": {"WHEAT": 3.0, "CORN": 2.4, "SUGAR_BEETS": 16.0}},
            probability=0.036,
        ),
        dict(
            ID="BVV",
            data={"Yield": {"WHEAT": 2.0, "CORN": 3.0, "SUGAR_BEETS": 20.0}},
            probability=0.027,
        ),
        dict(
            ID="AVV",
            data={"Yield": {"WHEAT": 3.0, "CORN": 3.0, "SUGAR_BEETS": 20.0}},
            probability=0.036,
        ),
        dict(
            ID="VBV",
            data={"Yield": {"WHEAT": 2.5, "CORN": 2.4, "SUGAR_BEETS": 20.0}},
            probability=0.027,
        ),
        dict(
            ID="VAV",
            data={"Yield": {"WHEAT": 2.5, "CORN": 3.6, "SUGAR_BEETS": 20.0}},
            probability=0.036,
        ),
        dict(
            ID="VVB",
            data={"Yield": {"WHEAT": 2.5, "CORN": 3.0, "SUGAR_BEETS": 16.0}},
            probability=0.027,
        ),
        dict(
            ID="VVA",
            data={"Yield": {"WHEAT": 2.5, "CORN": 3.0, "SUGAR_BEETS": 24.0}},
            probability=0.036,
        ),
        dict(
            ID="AAB",
            data={"Yield": {"WHEAT": 3.0, "CORN": 3.6, "SUGAR_BEETS": 16.0}},
            probability=0.048,
        ),
        dict(
            ID="AAV",
            data={"Yield": {"WHEAT": 3.0, "CORN": 3.6, "SUGAR_BEETS": 20.0}},
            probability=0.048,
        ),
        dict(
            ID="ABA",
            data={"Yield": {"WHEAT": 3.0, "CORN": 2.4, "SUGAR_BEETS": 24.0}},
            probability=0.048,
        ),
        dict(
            ID="AVA",
            data={"Yield": {"WHEAT": 3.0, "CORN": 3.0, "SUGAR_BEETS": 24.0}},
            probability=0.048,
        ),
        dict(
            ID="BAA",
            data={"Yield": {"WHEAT": 2.0, "CORN": 3.6, "SUGAR_BEETS": 24.0}},
            probability=0.048,
        ),
        dict(
            ID="VAA",
            data={"Yield": {"WHEAT": 2.5, "CORN": 3.6, "SUGAR_BEETS": 24.0}},
            probability=0.048,
        ),
        dict(
            ID="BVA",
            data={"Yield": {"WHEAT": 2.0, "CORN": 3.0, "SUGAR_BEETS": 24.0}},
            probability=0.036,
        ),
        dict(
            ID="BAV",
            data={"Yield": {"WHEAT": 2.0, "CORN": 3.6, "SUGAR_BEETS": 20.0}},
            probability=0.036,
        ),
        dict(
            ID="VBA",
            data={"Yield": {"WHEAT": 2.5, "CORN": 2.4, "SUGAR_BEETS": 24.0}},
            probability=0.036,
        ),
        dict(
            ID="VAB",
            data={"Yield": {"WHEAT": 2.5, "CORN": 3.6, "SUGAR_BEETS": 16.0}},
            probability=0.036,
        ),
        dict(
            ID="AVB",
            data={"Yield": {"WHEAT": 3.0, "CORN": 3.0, "SUGAR_BEETS": 16.0}},
            probability=0.036,
        ),
        dict(
            ID="ABV",
            data={"Yield": {"WHEAT": 3.0, "CORN": 2.4, "SUGAR_BEETS": 20.0}},
            probability=0.036,
        ),
    ]
}


#
# create the LF_data/HF_data dicts using per-plot scenarios
#
class LFScenario_dict(object):

    def __init__(self, LF_scendata):
        self.LF_scendata = LF_scendata

    def scenario_generator(self):
        """
        Create a dictionary with a single key, "scenarios", which maps
        to a list of scenario specifications.  The data for each scenario
        contains "list_IDs", which is the list of per-plot scenarios from
        HF_scendata contained in the scenario.
        """
        ### always samples the three original (LF) scenarios:
        HF_plot_scenarios = {scen["ID"]: scen for scen in HF_scendata["scenarios"]}
        plot_scenarios = [
            HF_plot_scenarios["BBB"],
            HF_plot_scenarios["VVV"],
            HF_plot_scenarios["AAA"],
        ]
        self.scen_dict = {
            "scenarios": [
                dict(
                    ID=f"scen_{s}",
                    data={"list_IDs": [plot_scen]},
                    probability=plot_scen["probability"],
                )
                for s, plot_scen in enumerate(plot_scenarios)
            ]
        }

        ### normalize scenario probabilities
        scenarios = self.scen_dict["scenarios"]
        norm_factor = sum(scen["probability"] for scen in scenarios)
        for scen in scenarios:
            scen["probability"] /= norm_factor

        return self.scen_dict


class HFScenario_dict(object):

    def __init__(self, HF_scendata):
        self.HF_scendata = HF_scendata

    def scenario_generator(self, num_plots, num_scens):
        """
        Create a dictionary with a single key, "scenarios", which maps
        to a list of scenario specifications.  The data for each scenario
        contains "list_IDs", which is the list of per-plot scenarios from
        HF_scendata contained in the scenario.
        """
        plot_scenarios = list(self.HF_scendata["scenarios"])

        def scen_prob(list_IDs):
            return math.prod(plot_scen["probability"] for plot_scen in list_IDs)

        ### the scenarios are randomly sampled:
        scen_list_IDs = [
            random.choices(plot_scenarios, k=num_plots) for s in range(num_scens)
        ]

        ### remove redundant scenarios (not the most elegant solution... but pretty sure it works):
        for u in range(num_scens):
            for s in range(u, num_scens):
                if scen_list_IDs[s] == scen_list_IDs[u]:
                    redundant_scen = scen_list_IDs[s]
                    new_scen = random.choices(plot_scenarios, k=num_plots)
                    while new_scen == redundant_scen:
                        new_scen = random.choices(plot_scenarios, k=num_plots)
                    scen_list_IDs[s] = new_scen

        ### normalize scenario probabilities
        norm_factor = sum(scen_prob(list_IDs) for list_IDs in scen_list_IDs)
        self.scen_dict = {
            "scenarios": [
                dict(
                    ID=f"scen_{s}",
                    data={"list_IDs": list_IDs},
                    probability=scen_prob(list_IDs) / norm_factor,
                )
                for s, list_IDs in enumerate(scen_list_IDs)
            ]
        }

        return self.scen_dict


#
# construct model_data:
#
HFScen_object = HFScenario_dict(HF_scendata)
HF_data = HFScen_object.scenario_generator(GlobalData.num_plots, GlobalData.num_scens)

app_data = {"num_plots": GlobalData.num_plots}
model_data = {"LF": LF_scendata, "HF": HF_data}


#
# Construct LF farmers problem model:
#
def LF_model_builder(data, args):
    num_plots = GlobalData.num_plots
    model = pyo.ConcreteModel(data["ID"])

    ### PARAMETERS
    model.TOTAL_ACREAGE = 500.0
    model.PLOTS = pyo.Set(initialize=[j for j in range(num_plots)])

    def crops_init(m):
        retval = []
        # for j in range(num_plots):
        retval.append("WHEAT")
        retval.append("CORN")
        retval.append("SUGAR_BEETS")
        return retval

    model.CROPS = pyo.Set(initialize=crops_init)

    def _scale_up_data(indict):
        outdict = {}
        # for j in range(num_plots):
        for crop in ["WHEAT", "CORN", "SUGAR_BEETS"]:
            outdict[crop] = indict[crop]
        return outdict

    model.PriceQuota = _scale_up_data(
        {"WHEAT": 100000.0, "CORN": 100000.0, "SUGAR_BEETS": 6000.0}
    )

    model.SubQuotaSellingPrice = _scale_up_data(
        {"WHEAT": 170.0, "CORN": 150.0, "SUGAR_BEETS": 36.0}
    )

    model.SuperQuotaSellingPrice = _scale_up_data(
        {"WHEAT": 0.0, "CORN": 0.0, "SUGAR_BEETS": 10.0}
    )

    model.CattleFeedRequirement = _scale_up_data(
        {"WHEAT": 200.0, "CORN": 240.0, "SUGAR_BEETS": 0.0}
    )

    model.PurchasePrice = _scale_up_data(
        {"WHEAT": 238.0, "CORN": 210.0, "SUGAR_BEETS": 100000.0}
    )

    model.PlantingCostPerAcre = _scale_up_data(
        {"WHEAT": 150.0, "CORN": 230.0, "SUGAR_BEETS": 260.0}
    )

    ### STOCHASTIC DATA
    def Yield_init(m, cropname):
        crop_base_name = cropname.rstrip("0123456789")
        return data["Yield"][crop_base_name]

    model.Yield = pyo.Param(
        model.CROPS, within=pyo.NonNegativeReals, initialize=Yield_init, mutable=True
    )

    ### VARIABLES
    if args.get("use_integer", True):
        model.DevotedAcreage = pyo.Var(
            model.CROPS,
            model.PLOTS,
            within=pyo.NonNegativeIntegers,
            bounds=(0.0, model.TOTAL_ACREAGE / num_plots),
        )
    else:
        model.DevotedAcreage = pyo.Var(
            model.CROPS, model.PLOTS, bounds=(0.0, model.TOTAL_ACREAGE / num_plots)
        )

    model.QuantitySubQuotaSold = pyo.Var(model.CROPS, bounds=(0.0, None))
    model.QuantitySuperQuotaSold = pyo.Var(model.CROPS, bounds=(0.0, None))
    model.QuantityPurchased = pyo.Var(model.CROPS, bounds=(0.0, None))

    ### CONSTRAINTS
    def ConstrainPerPlotAcreage_rule(model):
        return (
            sum(
                sum(model.DevotedAcreage[c, j] for j in model.PLOTS)
                for c in model.CROPS
            )
            <= model.TOTAL_ACREAGE
        )

    model.ConstrainPerPlotAcreage = pyo.Constraint(rule=ConstrainPerPlotAcreage_rule)

    if len(model.PLOTS) > 1:

        def ConsistentPerPlotAcreage_rule(model):
            return (
                0,
                sum(
                    sum(
                        model.DevotedAcreage[c, j]
                        for j in range(1, len(model.PLOTS) - 1)
                    )
                    for c in model.CROPS
                ),
                0,
            )

        model.ConsistentPerPlotAcreage = pyo.Constraint(
            rule=ConsistentPerPlotAcreage_rule
        )

    def EnforceCattleFeedRequirement_rule(model, c):
        return model.CattleFeedRequirement[c] <= model.Yield[c] * model.DevotedAcreage[
            c, 0
        ] + model.QuantityPurchased[c] - (
            model.QuantitySubQuotaSold[c] + model.QuantitySuperQuotaSold[c]
        )

    model.EnforceCattleFeedRequirement = pyo.Constraint(
        model.CROPS, rule=EnforceCattleFeedRequirement_rule
    )

    def LimitAmountSold_rule(model, c):
        return (
            model.QuantitySubQuotaSold[c]
            + model.QuantitySuperQuotaSold[c]
            - model.Yield[c] * model.DevotedAcreage[c, 0]
        ) <= 0.0

    model.LimitAmountSold = pyo.Constraint(model.CROPS, rule=LimitAmountSold_rule)

    def EnforceQuotas_rule(model, c):
        return (0.0, model.QuantitySubQuotaSold[c], model.PriceQuota[c])

    model.EnforceQuotas = pyo.Constraint(model.CROPS, rule=EnforceQuotas_rule)

    ### OBJECTIVE
    def ComputeFirstStageCost_rule(model):
        return sum(
            model.PlantingCostPerAcre[c] * model.DevotedAcreage[c, 0]
            for c in model.CROPS
        )

    model.FirstStageCost = pyo.Expression(rule=ComputeFirstStageCost_rule)

    def ComputeSecondStageCost_rule(model):
        expr = pyo.sum_product(model.PurchasePrice, model.QuantityPurchased)
        expr -= sum(
            model.SubQuotaSellingPrice[c] * model.QuantitySubQuotaSold[c]
            for c in model.CROPS
        )
        expr -= sum(
            model.SuperQuotaSellingPrice[c] * model.QuantitySuperQuotaSold[c]
            for c in model.CROPS
        )
        return expr

    model.SecondStageCost = pyo.Expression(rule=ComputeSecondStageCost_rule)

    def total_cost_rule(model):
        return model.FirstStageCost + model.SecondStageCost

    model.Total_Cost_Objective = pyo.Objective(rule=total_cost_rule, sense=pyo.minimize)

    return model


#
# Construct HF farmers problem model:
#
def model_builder(data, args):
    num_plots = GlobalData.num_plots
    model = pyo.ConcreteModel(data["ID"])

    ### PARAMETERS
    model.TOTAL_ACREAGE = 500.0
    model.PLOTS = pyo.Set(initialize=[j for j in range(num_plots)])

    def crops_init(m):
        retval = []
        retval.append("WHEAT")
        retval.append("CORN")
        retval.append("SUGAR_BEETS")
        return retval

    model.CROPS = pyo.Set(initialize=crops_init)

    def _scale_up_data(indict):
        outdict = {}
        for crop in ["WHEAT", "CORN", "SUGAR_BEETS"]:
            outdict[crop] = indict[crop]
        return outdict

    model.PriceQuota = _scale_up_data(
        {"WHEAT": 100000.0, "CORN": 100000.0, "SUGAR_BEETS": 6000.0}
    )

    model.SubQuotaSellingPrice = _scale_up_data(
        {"WHEAT": 170.0, "CORN": 150.0, "SUGAR_BEETS": 36.0}
    )

    model.SuperQuotaSellingPrice = _scale_up_data(
        {"WHEAT": 0.0, "CORN": 0.0, "SUGAR_BEETS": 10.0}
    )

    model.CattleFeedRequirement = _scale_up_data(
        {"WHEAT": 200.0, "CORN": 240.0, "SUGAR_BEETS": 0.0}
    )

    model.PurchasePrice = _scale_up_data(
        {"WHEAT": 238.0, "CORN": 210.0, "SUGAR_BEETS": 100000.0}
    )

    model.PlantingCostPerAcre = _scale_up_data(
        {"WHEAT": 150.0, "CORN": 230.0, "SUGAR_BEETS": 260.0}
    )

    ### STOCHASTIC DATA
    def Yield_init(m, cropname, plot):  ### per-plot crop yields
        crop_base_name = cropname.rstrip("0123456789")
        return data["list_IDs"][plot]["data"]["Yield"][crop_base_name]

    model.Yield = pyo.Param(
        model.CROPS,
        model.PLOTS,
        within=pyo.NonNegativeReals,
        initialize=Yield_init,
        mutable=True,
    )

    ### VARIABLES
    if args.get("use_integer", True):
        model.DevotedAcreage = pyo.Var(
            model.CROPS,
            model.PLOTS,
            within=pyo.NonNegativeIntegers,
            bounds=(0.0, model.TOTAL_ACREAGE / num_plots),
        )
    else:
        model.DevotedAcreage = pyo.Var(
            model.CROPS, model.PLOTS, bounds=(0.0, model.TOTAL_ACREAGE / num_plots)
        )

    model.QuantitySubQuotaSold = pyo.Var(model.CROPS, model.PLOTS, bounds=(0.0, None))
    model.QuantitySuperQuotaSold = pyo.Var(model.CROPS, model.PLOTS, bounds=(0.0, None))
    model.QuantityPurchased = pyo.Var(model.CROPS, bounds=(0.0, None))

    ### CONSTRAINTS
    def ConstrainPerPlotAcreage_rule(model, j):
        return (
            sum(model.DevotedAcreage[c, j] for c in model.CROPS)
            <= model.TOTAL_ACREAGE / num_plots
        )

    model.ConstrainPerPlotAcreage = pyo.Constraint(
        model.PLOTS, rule=ConstrainPerPlotAcreage_rule
    )

    def EnforceCattleFeedRequirement_rule(model, c):
        return model.CattleFeedRequirement[c] <= sum(
            model.Yield[c, j] * model.DevotedAcreage[c, j] for j in model.PLOTS
        ) + model.QuantityPurchased[c] - sum(
            model.QuantitySubQuotaSold[c, j] + model.QuantitySuperQuotaSold[c, j]
            for j in model.PLOTS
        )

    model.EnforceCattleFeedRequirement = pyo.Constraint(
        model.CROPS, rule=EnforceCattleFeedRequirement_rule
    )

    def LimitAmountSold_rule(model, c, j):
        return (
            model.QuantitySubQuotaSold[c, j]
            + model.QuantitySuperQuotaSold[c, j]
            - model.Yield[c, j] * model.DevotedAcreage[c, j]
            <= 0.0
        )

    model.LimitAmountSold = pyo.Constraint(
        model.CROPS, model.PLOTS, rule=LimitAmountSold_rule
    )

    def EnforceQuotas_rule(model, c):
        return (
            0.0,
            sum(model.QuantitySubQuotaSold[c, j] for j in model.PLOTS),
            model.PriceQuota[c],
        )

    model.EnforceQuotas = pyo.Constraint(model.CROPS, rule=EnforceQuotas_rule)

    ### OBJECTIVE
    def ComputeFirstStageCost_rule(model):
        return sum(
            model.PlantingCostPerAcre[c]
            * sum(model.DevotedAcreage[c, j] for j in model.PLOTS)
            for c in model.CROPS
        )

    model.FirstStageCost = pyo.Expression(rule=ComputeFirstStageCost_rule)

    def ComputeSecondStageCost_rule(model):
        expr = pyo.sum_product(model.PurchasePrice, model.QuantityPurchased)
        expr -= sum(
            model.SubQuotaSellingPrice[c]
            * sum(model.QuantitySubQuotaSold[c, j] for j in model.PLOTS)
            for c in model.CROPS
        )
        expr -= sum(
            model.SuperQuotaSellingPrice[c]
            * sum(model.QuantitySuperQuotaSold[c, j] for j in model.PLOTS)
            for c in model.CROPS
        )
        return expr

    model.SecondStageCost = pyo.Expression(rule=ComputeSecondStageCost_rule)

    def total_cost_rule(model):
        return model.FirstStageCost + model.SecondStageCost

    model.Total_Cost_Objective = pyo.Objective(rule=total_cost_rule, sense=pyo.minimize)

    return model


#
# options to solve, LF, HF, or MF:
#


def HF_farmers():
    sp = stochastic_program(first_stage_variables=["DevotedAcreage[*,*]"])
    sp.initialize_application(app_data=app_data)
    sp.initialize_model(
        name="HF", model_data=model_data["HF"], model_builder=model_builder
    )
    return Munch(sp=sp)


def LF_farmers():
    sp = stochastic_program(first_stage_variables=["DevotedAcreage[*,*]"])
    sp.initialize_application(app_data=app_data)
    sp.initialize_model(
        name="LF", model_data=model_data["LF"], model_builder=LF_model_builder
    )
    return Munch(sp=sp)


def MFrandom_farmers():
    sp = stochastic_program(first_stage_variables=["DevotedAcreage[*,*]"])
    sp.initialize_application(app_data=app_data)
    sp.initialize_model(
        name="HF", model_data=model_data["HF"], model_builder=model_builder
    )
    sp.initialize_model(
        name="LF",
        model_data=model_data["LF"],
        model_builder=LF_model_builder,
        default=False,
    )
    sp.initialize_bundles(
        scheme="mf_random",
        LF=2,
        seed=1234567890,
        model_weight={"HF": 2.0, "LF": 1.0},
    )
    return Munch(sp=sp)
