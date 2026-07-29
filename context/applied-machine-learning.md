The ML pipeline uses **two models that serve different purposes**:

1. **K-Means** discovers groups of factories that have similar weekly electricity consumption patterns.
2. **Random Forest** learns how to predict which group a new factory belongs to using only information that a user can easily provide.

Together, they solve the problem of **estimating an hourly electricity load profile for a factory when no historical smart-meter data exists**. This hourly profile is later matched against hourly solar generation to evaluate rooftop solar system performance. 

---

# 1. K-Means Clustering

### Purpose

The project first generates a synthetic dataset representing many different factories (because real Egyptian interval-meter data was unavailable).

Each synthetic factory has an **hourly electricity profile for an entire week (168 hours)**.

K-Means groups factories whose weekly load profiles have similar shapes.

Instead of manually defining load profile categories, K-Means automatically discovers them. 

---

### Inputs

For each synthetic factory, K-Means receives:

* A normalized weekly electricity load profile
* 168 hourly values (24 × 7 days)

These values describe **how electricity demand changes throughout the week**, independent of total energy consumption. 

---

### Output

K-Means predicts:

* A **cluster ID**

Each cluster represents a characteristic load pattern, such as:

* daytime factories
* continuous-operation factories
* two-shift factories

The project also computes the **average load profile (cluster centroid)** for every cluster, which becomes the representative profile used later during prediction. 

---

# 2. Random Forest Classifier

### Purpose

A new factory does **not** have a known hourly load profile.

Instead, the user only knows simple business information.

The Random Forest learns the relationship between those business characteristics and the clusters discovered by K-Means.

Its job is therefore:

> Predict which load-profile cluster a new factory most likely belongs to.



---

### Inputs

The Random Forest receives user-friendly factory information:

* Factory sector
* Shift pattern
* Working days per week
* Shift start hour
* Shift end hour

These are converted into simple numerical features before training. 

---

### Output

The Random Forest predicts:

* the most likely **cluster ID**
* the probability (confidence) of that prediction

If confidence is high enough, the system uses that cluster's average weekly load profile.

If confidence is low, the system ignores the ML prediction and falls back to the deterministic baseline model to avoid unreliable predictions. 

---

# Overall Problem Being Solved

The project aims to estimate a factory's **hourly electricity demand profile** without requiring historical smart-meter measurements.

Knowing only a few characteristics of the factory, the system predicts what its electricity usage probably looks like throughout the day and week.

This estimated load profile is then used to:

* compare electricity demand with solar generation,
* estimate self-consumption,
* size rooftop PV systems,
* calculate expected savings and payback period.

The ML approach improves over using one fixed predefined load profile by allowing factories with similar characteristics to be matched to more representative consumption patterns.

---

# Model Performance Metrics

The project evaluates both the clustering quality and the classification performance.

### 1. Silhouette Score

Used to evaluate the **K-Means clustering**.

It measures how well separated the discovered clusters are.

* Higher values indicate factories within the same cluster are similar while different clusters are well separated.

It is also used to automatically choose the optimal number of clusters. 

---

### 2. Classification Accuracy

Used to evaluate the **Random Forest classifier**.

It measures the percentage of factories whose cluster was predicted correctly.

The project reports:

* classifier test accuracy
* baseline lookup accuracy

allowing the ML classifier to be directly compared against a simple deterministic lookup method. 

---

### 3. Adjusted Rand Index (ARI)

Used to evaluate how closely the clusters produced by K-Means match the known synthetic factory categories.

Since the training data is synthetic and generated from predefined archetypes, ARI measures whether the clustering successfully recovers those underlying groups.

Higher values indicate better agreement. 

---

# Summary

| Model             | Inputs                                                      | Predicts                             | Purpose                                                                                                  |
| ----------------- | ----------------------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| **K-Means**       | 168-hour normalized weekly load profile                     | Cluster ID                           | Groups factories with similar electricity consumption patterns and creates representative load profiles. |
| **Random Forest** | Sector, shift pattern, working days, shift start, shift end | Cluster ID and prediction confidence | Assigns a new factory to the most appropriate load-profile cluster using simple user inputs.             |

The two models work together: **K-Means first discovers representative electricity consumption patterns, and the Random Forest then learns how to assign new factories to those patterns based on easily available factory characteristics.** If the classifier is not confident, the system safely falls back to the deterministic archetype-based model instead of making an uncertain ML prediction.
