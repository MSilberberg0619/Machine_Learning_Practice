import os
import tarfile
from six.moves import urllib
import pandas as pd
from pandas.plotting import scatter_matrix
import matplotlib.pyplot as plt
import numpy as np
from zlib import crc32 #For compressing data...
from sklearn.model_selection import train_test_split, StratifiedShuffleSplit, cross_val_score, GridSearchCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder, StandardScaler
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor

####################################################################################################
#This block of code is because Scikit-Learn 0.20 replaced sklearn.preprocessing.Imputer class with
#sklearn.impute.SimpleImputer class

# try:
#     from sklearn.impute import SimpleImputer # Scikit-Learn 0.20+
# except ImportError:
#     from sklearn.preprocessing import Imputer as SimpleImputer
####################################################################################################

DOWNLOAD_ROOT = "https://raw.githubusercontent.com/ageron/handson-ml/master/"
HOUSING_PATH = os.path.join("datasets", "housing")
HOUSING_URL = DOWNLOAD_ROOT + "datasets/housing/housing.tgz"

#Custom transformer to add attributes
class CombinedAttributesAdder(BaseEstimator, TransformerMixin):
    def __init__(self, add_bedrooms_per_room = True): #No *args or **kargs
        self.add_bedrooms_per_room = add_bedrooms_per_room
    def fit(self, X, y=None):
        return self #Nothing else to do
    def transform(self, X, y=None):
        room_per_household = X[:, rooms_ix] / X[:, households_ix]
        population_per_household = X[:, population_ix] / X[:, households_ix]
        if self.add_bedrooms_per_room:
            bedrooms_per_room = X[:, bedrooms_ix] / X[:, rooms_ix]
            return np.c_[X, room_per_household, population_per_household, bedrooms_per_room]
        else:
            return np.c_[X, room_per_household, population_per_household]

#This transformer has one hyperparamter, "add_bedrooms_per_room", set to True by default and can easily allow for the
#determination of whether adding this attribute helps the Machine Learning algorithm (gate the data by adding
#a hyperparamter you are not %100 sure about

def fetch_housing_data(housing_url=HOUSING_URL, housing_path=HOUSING_PATH):

    if not os.path.isdir(housing_path):
        os.makedirs(housing_path)
    tgz_path = os.path.join(housing_path, "housing.tgz")
    urllib.request.urlretrieve(housing_url, tgz_path)
    housing_tgz = tarfile.open(tgz_path)
    housing_tgz.extractall(path=housing_path)
    housing_tgz.close()

def load_housing_data(housing_path=HOUSING_PATH):
    csv_path = os.path.join(housing_path, "housing.csv")
    return pd.read_csv(csv_path)

# This is not the best method to generate test data...
def split_train_test(data, test_ratio):
    shuffled_indices = np.random.permutation(len(data)) #Randomly shuffles data around
    test_set_size = int(len(data) * test_ratio)
    test_indices = shuffled_indices[:test_set_size]
    train_indices = shuffled_indices[test_set_size:]
    return data.iloc[train_indices], data.iloc[test_indices]

def test_set_check(identifier, test_ratio):
    return crc32(np.int64(identifier)) & 0xffffffff < test_ratio * 2**32

if __name__ == "__main__":

    fetch_housing_data()

    #"housing" is a Pandas data frame
    housing = load_housing_data()
    print(housing.head())
    print(housing.info())
    # print(housing["longitude"].value_counts())
    print(housing.describe())

    housing.hist(bins=50, figsize=(20,15))
    #plt.show()

    #Split dataframe into random training and test sets
    train_set, test_set = train_test_split(housing, test_size=0.2, random_state=42)
    print(train_set)
    print(test_set)

    #Bin data into discrete intervals
    housing["income_cat"] = pd.cut(housing["median_income"], bins=[0, 1.5, 3.0, 4.5, 6., np.inf], labels=[1, 2, 3, 4, 5])
    plt.show(housing["income_cat"].hist()) #Now I can do Stratified Sampling (See Book)

    #Prepare data for stratified sampling
    split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    for train_index, test_index in split.split(housing, housing["income_cat"]): #This Function Performs Stratified Sampling Based on the Income Category (Recall Male and Female Example...)
        strat_train_set = housing.loc[train_index]
        strat_test_set = housing.loc[test_index] #.loc can access a group of rows or columns by label(s)

    print(strat_test_set["income_cat"].value_counts()/len(strat_test_set)) #Compare to Histogram to See if Ratio of Test Set Data Matches the Height of the Bars

    train_set, test_set = train_test_split(housing, test_size=0.2, random_state=42)

    compare_props = pd.DataFrame({
        "Overall": housing["income_cat"].value_counts()/len(housing),
        "Stratified": strat_test_set["income_cat"].value_counts()/len(strat_test_set),
        "Random": test_set["income_cat"].value_counts()/len(test_set)
    }).sort_index()
    compare_props["Rand. %Error"] = 100 * compare_props["Random"] / compare_props["Overall"] - 100
    compare_props["Strat. %Error"] = 100 * compare_props["Stratified"] / compare_props["Overall"] - 100

    print(compare_props)

    for set_ in(strat_train_set, strat_test_set): #Removing the "Income Category (income_cat) Attribute...
        set_.drop("income_cat", axis=1, inplace=True)

    #Create a Copy of the Training Set so the Original is not Harmed
    housing = strat_train_set.copy()

    #Visualize the Data in a Scatterplot
    plt.show(housing.plot(kind='scatter', x="longitude", y="latitude", alpha=0.1)) #alpha Helps Highlight High Density Areas

    housing.plot(kind='scatter', x='longitude', y='latitude', alpha=0.4,
                 s=housing["population"]/100, label="population", figsize=(10,7),
                 c="median_house_value", cmap=plt.get_cmap("jet"), colorbar=True,)
    #plt.show()

    #Look at how each Attribute Correlates with Median House Value (Median House Value is the "Target" Attribute)
    corr_matrix = housing.corr()
    print(corr_matrix["median_house_value"].sort_values(ascending=False))

    attributes = ["median_house_value", "median_income", "total_rooms", "housing_median_age"]
    scatter_matrix(housing[attributes], figsize=(12,8))
    #plt.show()

    housing.plot(kind="scatter", x="median_income", y="median_house_value",
                 alpha=0.1)
    #plt.show()

    #Try Different Combinations of Attributes Before Feeding Data to Machine Learning Algorithm

    housing["rooms_per_household"] = housing["total_rooms"]/housing["households"]
    housing["bedrooms_per_room"] = housing["total_bedrooms"]/housing["total_rooms"]
    housing["population_per_household"] = housing["population"]/housing["households"]

    #See How Many Attributes There Are
    # print(housing.info())
    # print(housing.describe())

    #Look at Correlation Matrix Again with Median House Value as the Target Value
    corr_matrix = housing.corr()
    corr_matrix["median_house_value"].sort_values(ascending=False)

    #The Result: "bedrooms_per_room" is more correlated than "total_room" or "total_bedrooms" with Median Housing Value

    #Next, the data will be prepared for machine learning algorithms
    #First, we will revert to a clean training set. The predictors and labels will be separated since we
    #don't want to apply the same transformation to the predictors and the target values

    #Creates a Copy of the Data "strat_train_set"
    #The predictors and labels are separated since we don't want to necessarily apply the same transformations to the
    #predictors and target values
    housing = strat_train_set.drop("median_house_value", axis=1) #Drop "median_house_value" from training set and creates a copy of the training set
    ###NOTE: I believe "median_house_value" was dropped because we are separating the predictors and labels...###
    print(housing)
    #Create a copy of the "median_house_value" attribute and make it the target
    housing_labels = strat_train_set["median_house_value"].copy()
    print(housing.info())

    #Sample incomplete rows
    sample_incomplete_rows = housing[housing.isnull().any(axis=1)].head()
    print(sample_incomplete_rows)

    print(housing_labels) #Print Training Set (This is only the "median_house_value" attribute)

    #Recall: At this point, the "total-bedrooms" attribute is missing some values
    #There are three options to take care of the attribute's missing values:
    #1.) Get rid of the corresponding districts (rows)
    #2.) Get rid of the whole attribute
    #3.) Set the values to some value (zero, mean, median etc.)
    housing.dropna(subset=["total_bedrooms"])   #Option #1.)
    housing.drop("total_bedrooms", axis=1)      #Option #2.)
    median = housing["total_bedrooms"].median() #Option #3.)
    housing["total_bedrooms"].fillna(median, inplace=True) #Whatever this median value is, save it -> We will need it
    #later to replace missing values in the test set


    #Use Scikit-Learn modules to take care of missing values: SimpleInputer

    #First, create instance of SimpleInputer and specify that you want to replace each attribute's missing values with
    #the median of the attribute
    imputer = SimpleImputer(strategy="median")


    #Because the median can only be computed on numerical attributes, we need to copy the data without text attribute
    #"ocean_proximity"
    housing_num = housing.drop("ocean_proximity", axis=1)

    #Now fit the Imputer instance to the training date using the fit() method
    imputer.fit(housing_num) #<-- Computed the median of each attribute and stored the results in its statistics_
    #instance variable

    #Since only "total_bedrooms" attribute was missing date, it only computed median values for that attribute, but
    #once the system goes live there can be more missing attributes, so it's better to apply the Imputer to all of the
    #numerical attributes
    print(imputer.statistics_)
    print(housing_num.median().values) #<-- This is just checking to ensure manually computing the median of the
    #attribute is the same as using the imputter.fit

    #Replace missing values in training set by learned medians (Transform the training set)
    #Note: 433 is the median of the "total_bedrooms" attribute
    X = imputer.transform(housing_num)
    print(imputer.strategy)

    #The result is a plain Numpy array containing the transformed features. Now we can put it back into a Pandas
    #DataFrame using the following:
    housing_tr = pd.DataFrame(X, columns=housing_num.columns, index=housing.index) #housing_num does not include
    #"ocean_proximity" attribute

    print("\nThis is the housing.index values:")
    print(housing.index)

    #Since we already stored the incomplete rows in
    #"sample_incomplete_rows", we're just checking to ensure those values were replaced with the median

    #Recall: the ".loc" locates values in a Pandas DataFrame  <-- see documentation
    print(housing_tr.loc[sample_incomplete_rows.index.values])

    #NOTE: For pushing "bare" repo to Github: $ git remote add origin https://github.com/MSilberberg0619/Machine_Learning_Practice.git

    #"ocean_proximity" was left out because it's a text attribute and so the median can't be computed
    #To fix, convert these categories from text to numbers using Scikit-Learn's OrdinalEncoder class
    housing_cat = housing[["ocean_proximity"]]
    print(housing_cat.head(10))

    ordinal_encoder = OrdinalEncoder()
    housing_cat_encoded = ordinal_encoder.fit_transform(housing_cat)
    print(housing_cat_encoded)

    #Can use one-hot encoding to map attributes to categories so the values of the attributes that are more similar
    #will have similar encoded values
    #We don't want the model to assume some natural ordering to the data --> could result in poor performance or
    #unexpected results
    cat_encoder = OneHotEncoder()
    housing_cat_1hot = cat_encoder.fit_transform(housing_cat)
    print(housing_cat_1hot)
    housing_cat_1hot.toarray()
    print(housing_cat_1hot)

    #List of categories using the encoder's categories instance variable
    print(cat_encoder.categories_)

    #May need to write custom transformations for tasks such as custom cleanup operations
    #This transformer class adds the combined attributes discussed earlier
    rooms_ix, bedrooms_ix, population_ix, households_ix = 3, 4, 5, 6 #Line 1.1

    # get the right column indices: safer than hard-coding indices 3, 4, 5, 6
    rooms_ix, bedrooms_ix, population_ix, household_ix = [           #Line 1.2
        list(housing.columns).index(col)
        for col in ("total_rooms", "total_bedrooms", "population", "households")]

    #NOTE: Line 1.1 and Line 1.2 provide the same result, but Line 1.2 is safer, as noted

    #Call Instance of "CombinedAttributesAdder Class
    attr_adder = CombinedAttributesAdder(add_bedrooms_per_room=False) #Call "CombinedAttributesAdder" constructor
    housing_extra_attribs = attr_adder.transform(housing.values) #Call method from "CombinedAttributesAdder class

    #Because PyCharm can such sometimes, see "Feature Scaling" on page 66 for information about one of the most
    #important transformations: feature scaling. There are two common ways: MinMax (Normalization) and
    #Standardization (Convert to Standard Normal Distribution)

    #Standardization of a dataset is a common requirement for many machine learning estimators: they might behave badly
    # if the individual features do not more or less look like standard normally distributed data
    # (e.g. Gaussian with 0 mean and unit variance).

    #Scikit-Learn provides the "Pipeline" class to help with the sequence of transformations
    num_pipeline = Pipeline([   #<-- Pipeline constructor takes a list of name/estimator pairs
        ('imputer', SimpleImputer(strategy="median")),
        ('attribs_adder', CombinedAttributesAdder()),
        ('std_scaler', StandardScaler()),
    ]) #<-- All but last estimator must be transformers (must have a fit_transform() method)

    housing_num_tr = num_pipeline.fit_transform(housing_num) #Utilize numerical pipeline provided by "Pipeline" class

    #Calling the "Pipeline's" fit method calls fit_method() sequentially on all transformers, passing the output of each
    #call as the parameter to the next call, until it reaches the final estimator which then the fit() method is called

    #From the Scikit-Learn website: Sequentially apply a list of transforms and a final estimator. Intermediate steps of
    # the pipeline must be ‘transforms’, that is, they must implement fit and transform methods. The final estimator
    # only needs to implement fit. The transformers in the pipeline can be cached using memory argument

    #Use ColumnTransformer from Scikit-Learn to apply transformation to all columns, whether categorical or numerical
    num_attribs = list(housing_num)
    cat_atribs = ["ocean_proximity"]

    full_pipeline = ColumnTransformer([
        ("num", num_pipeline, num_attribs),   #<-- Returns a dense matrix
        ("cat", OneHotEncoder(), cat_atribs), #<-- Returns a sparse matrix
    ]) #<-- Group together categorical and numerical column names and construct a ColumnTransformer
    #Constructor requires a list of tuples with name, a transformer and a list of names (or indices) of columns that the
    #transformer should be applied to
    #1.) Numerical columns are transformed with the num_pipeline defined earlier
    #2.) Categorical columns should be transformed using a OneHotEncoder
    #Apply this ColumnTransformer to the housing data --> applies each transformer to the appropriate columns and
    #concatenates the outputs along the second axis
    housing_prepared = full_pipeline.fit_transform(housing)

    #Train a Machine Learning model using linear regression
    lin_reg = LinearRegression()
    lin_reg.fit(housing_prepared, housing_labels)

    #Try linear regression model out on a few instances from teh training set!
    some_data = housing.iloc[:5]
    some_labels = housing_labels.iloc[:5]
    some_data_prepared = full_pipeline.transform(some_data)
    print("Predictions:" ,lin_reg.predict(some_data_prepared))
    print('\n')
    print("Labels: ", list(some_labels))

    #Measure the regression model's RMSE on the whole training set using Scikit-Learn's "mean_squared_error" function
    housing_predictions = lin_reg.predict(housing_prepared)
    lin_mse = mean_squared_error(housing_labels, housing_predictions)
    lin_rmse = np.sqrt(lin_mse)
    print(lin_rmse) #<-- Model underfit the training data... (median_housing_values is between $120,000 and $265,000)

    #The underfitting of the model says two things:
    #1.) The features do not provide enough information to make good predictions
    #2.) The model is not powerful enough

    #Try to train with a DecisionTreeRegressor --> This is a powerful model that is capable of finding nonlinear
    #relationships in the data (Decision Trees will be presented in more detail in Chapter 4)
    tree_reg = DecisionTreeRegressor()
    tree_reg.fit(housing_prepared, housing_labels) #<-- Training the model

    housing_predictions = tree_reg.predict(housing_prepared) #<-- Test the trained model using the training set
    tree_mse = mean_squared_error(housing_labels, housing_predictions)
    tree_rmse = np.sqrt(tree_mse)
    print(tree_rmse)

    #This gave an error of zero, but this is likely not possible. It is more likely that the model badly overfit the
    #data. What'st he reason we believe this: Earlier, it was discussed that we don't want to touch the test set until
    #we're ready to launch, so we should instead use part of the training set for training and part for model validation

    #One way to evaluate the Decision Tree model would be to use the train_test_split function to split the
    #training set into a smaller training set and a validation set, then train the models against the smaller
    #training set and evaluate them against the validation set

    #An alternative is to use Scikit-Learn's "cross-validation" feature that performs K-fold cross validation
    #K-fold cross validation: Randomly splits the training set into 10 distinct subsets (folds), then it trains and
    #evaluates the Decision Tree model 10 times, picking a different fold (subset) every evaluation time and
    #training on the other 9 folds (subsets). This results in an array containing the 10 evaluation scores
    scores = cross_val_score(tree_reg, housing_prepared, housing_labels, scoring="neg_mean_squared_error",
                             cv=10)
    tree_rmse_scores = np.sqrt(-scores) #<-- Cross-validation expects a utility function instead of a cost function,
    #so the scoring function os actually the OPPOSITE of the MSE (negative value)
    print(tree_rmse_scores)
    print("Scores: ", tree_rmse_scores)
    print("Mean: ", tree_rmse_scores.mean())
    print("Standard Deviation: ", tree_rmse_scores.std())

    #Compute the same scores for the Linear Regression model
    lin_scores = cross_val_score(lin_reg, housing_prepared, housing_labels, scoring="neg_mean_squared_error",
                                 cv=10)
    lin_rmse_scores = np.sqrt(-lin_scores)
    print(lin_rmse_scores)
    print("Scores: ", lin_rmse_scores)
    print("Mean: ", lin_rmse_scores.mean()) #<-- Ten different rmse errors
    print("Standard Deviation: ", lin_rmse_scores.std())

    #Decision Tree is overfitting so badly that it performs worse than the Linear Regression model

    ################################### Aside ####################################################
    #Cross-validation uses all of the data, one block at a time, to train a model and summarizes the
    #results at the end

    #In the end, every block of data is used for testing and we can compare methods by seeing how well
    #they performed

    #Can also use K-fold cross-validation to find the best value for a tuning parameter

    #Essentially, 9 blocks of data are used for training and one for testing
    ##############################################################################################

    #Try one more last model for now: RandomForestRegressor --> This is a Random Forest that works by training many
    #Decision Trees on random subsets of the features, then averaging out their predictions.
    forest_reg = RandomForestRegressor() #<-- Create an instance of the method from the Scikit-Learn package
    forest_reg.fit(housing_prepared, housing_labels) #<-- Train the model
    housing_predictions = forest_reg.predict(housing_prepared)  # <-- Test the trained model using the training set
    forest_mse = mean_squared_error(housing_labels, housing_predictions)
    forest_rmse = np.sqrt(forest_mse)
    print(forest_rmse)

    # Compute the same scores for the Random Forest model
    forest_scores = cross_val_score(forest_reg, housing_prepared, housing_labels, scoring="neg_mean_squared_error",
                                 cv=10)
    forest_rmse_scores = np.sqrt(-forest_scores)
    print(forest_rmse_scores)
    print("Scores: ", forest_rmse_scores) #<-- Ten different rmse errors
    print("Mean: ", forest_rmse_scores.mean())
    print("Standard Deviation: ", forest_rmse_scores.std())

    #NOTE: Building a model on top of manu other models is called Ensemble Learning
    #The results show that the Random Forests perform better than the other two models, but the score on the training
    #set is still much lower than on the validation sets, indicating that the model is still overfitting the training
    #set. Some possible solutions to mitigate overfitting are as follows:
    # 1.) Simplify the model
    # 2.) Constrain it (regularize it)
    # 3.) Get more training data

    #Now it's time to fine-tune the list of selected models...
    #One method is to use Scikit-Learn's GridSearchCV to search for viable hyperparameters --> Just tell the method
    #which hyperparameters you want to experiment with and which values to try out and it will evaluate all the possible
    #combinations of hyperparameters using cross-validation

    #This code will search for the best combination of hyperparameter values for the RandomForestRegressor method

    #The param_grid tells Scikit-Learn to first evaluate all 3 x 4 = 12 combinations of n_estimators and max_features
    #hyperparameter values specified in the first dict (see first row in param_grid), then try all 2 x 3 = 6 combinations
    #of hyperparameter values in the second dict (see second row in param_grid), but this time with the bootstrap
    #hyperparameter set to False instead of True

    #The grid search will ultimately explore 18 combinations of RandomForestRegressor hyperparameter values and will
    #train each model five times (we are using five-fold cross validation). This results in a total of 18 x 5 = 90
    #rounds of training!
    param_grid = [
        {'n_estimators': [3, 10, 30], 'max_features': [2, 4, 6, 8]},
        {'bootstrap': [False], 'n_estimators': [3, 10], 'max_features': [2, 3, 4]}, #n_estimators is used when you have
        #have no idea what the hyperparameter values should be (one strategy is to try out consecutive power of 10)
    ]

    forest_reg = RandomForestRegressor()

    grid_search = GridSearchCV(forest_reg, param_grid, cv=5,
                               scoring='neg_mean_squared_error',
                               return_train_score=True)

    grid_search.fit(housing_prepared, housing_labels)

    print(grid_search.best_params_) #<-- The results are the maximum values that were evaluated, so we may want to
    #search again
    print(grid_search.best_estimator_)

    #If GridSearchCV is intitialized with refit=True --> retrains the whole training set once it find the best
    #estimator using cross-validation (usually a good performance boost)

    cvres = grid_search.cv_results_
    for mean_score, params in zip(cvres["mean_test_score"], cvres["params"]):
        print(np.sqrt(-mean_score), params)

    #The RMSE we obtained by iterating through the hyperparameter values is slightly better than the score we received
    #from the default hyperparameter values. Thus we successfully fine-tuned the model

    #We can also treat the data preparation steps as hyperparameter --> for example, we can determine whether to include
    #a certain feature such as the "add_bedrooms_per_room", we can use this feature as a hyperparameter in the
    #"CombinedAttributesAdder" transformer. We can also use it to determine how to handle outliers, missing features,
    #feature selection and more

    ####################################################################################################################
    #Grid search is sufficient when we are exploring few combinations, but if the hyperparameter search space is
    #large, we should use "RandomizedSearchCV" instead --> instead of trying out all possible combinations like when
    #we used "GridSearchCV", we use a given number of random combinations by selecting a random value for each
    #hyperparameter at every iteration. There are two benefits to this approach:
    # 1.) If the randomized search runs for 1,000 iterations, this approach will explore 1,000 different values for
    #     each hyperparameter
    # 2.) We have more control over the computing budget you want to allocate to hyperparameter search just by
    #     adjusting the number of iterations

    #We can also use ensemble methods, such as the Random Forest instead of Decision Trees, to fine-tune the system
    ####################################################################################################################

    #We can gain insight by inspecting the best models and determine the relative importance of each attribute for
    #making accurate predictions and drop less useful features.
    # feature_importances = grid_search.best_estimator_
    # # print(feature_importances)
    #
    # extra_attribs = ["rooms_per_household", "pop_per_household", "bedrooms_per_household"]
    # cat_encoder = full_pipeline.named_transformers_["cat"]
    # cat_one_hot_attribs = list(cat_encoder.categories_[0])
    # attributes = num_attribs + extra_attribs + cat_one_hot_attribs
    # sorted(zip(feature_importances, attributes), reverse=True)

    #Once we have a system that performs well from tweaking the models, we can evaluate the final model on the test set
    # To do this:
    # 1.) Get the predictors and labels from the test set
    # 2.) Run "full_pipeline()" to transform the data (call "transform()" not "fit_transform()") --> don't want to
    #     fit the test set!
    # 3.) Evaluate the final model on the test set

    final_model = grid_search.best_estimator_

    X_test = strat_test_set.drop("median_house_value", axis=1)
    y_test = strat_test_set["median_house_value"].copy()

    X_test_prepared = full_pipeline.transform(X_test)

    final_predictions = final_model.predict(X_test_prepared)

    final_mse = mean_squared_error(y_test, final_predictions)
    final_rmse = np.sqrt(final_mse)
    print(final_rmse) #<-- Performance may be worse than what was resolved with cross-validation if you did a lot of
    #hyperparameter tuning (end up with fine-tuned system that performs well on the validation data). However, if this
    #happens, DON'T TWEAK THE HYPERPARAMETERS TO MAKE THE DATA LOOK GOOD ON THE TEST SET; the improvements may still
    #not generalize to new data

    ####################################################################################################################
    #Now that the system is ready to launch, we need to plug in production input data sources and write tests. Also, we
    #should monitoring code to check the system's live performance at regular intervals and trigger alerts when it
    #drops --> Models tend to "rot" over time, unless the models are regularly trained on fresh data

    #Next, we should sample the system's predictions and evaluate them to evaluate the system's performance, which will
    #require a human analysis. There should be a human evaluation pipeline in the system.

    #We should also evaluate the system's input quality --> drop in performance can sometimes be due to a poor quality
    #signal (malfunctioning sensor reading etc.). By monitoring the system's inputs this degradation can be caught
    #much earlier.

    #Finally, we should train models on a regular basis using fresh data with an automated prcess --> if not, a sparsely
    #refreshed model and drop in performance or performance fluctuations may occur. If it's an online learning system,
    #it's a good idea to save snapshots of its state at regular intervals so we can go back to that state if needed.
    ####################################################################################################################