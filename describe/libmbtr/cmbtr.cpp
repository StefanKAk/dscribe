#include "cmbtr.h"
#include <vector>
#include <map>
#include <tuple>
#include <math.h>
#include <string>
#include <numeric>
#include <utility>
#include <cmath>
#include <algorithm>
#include <sstream>
#include <stdexcept>
using namespace std;

CMBTR::CMBTR(vector<vector<float> > positions, vector<int> atomicNumbers, map<int,int> atomicNumberToIndexMap, int cellLimit)
    : positions(positions)
    , atomicNumbers(atomicNumbers)
    , atomicNumberToIndexMap(atomicNumberToIndexMap)
    , cellLimit(cellLimit)
    , displacementTensorInitialized(false)
    , k2IndicesInitialized(false)
    , k3IndicesInitialized(false)
    , k2MapInitialized(false)
    , k3MapInitialized(false)
{
}

vector<vector<vector<float> > > CMBTR::getDisplacementTensor()
{
    // Use cached value if possible
    if (!this->displacementTensorInitialized) {
        int nAtoms = this->atomicNumbers.size();

        // Initialize tensor
        vector<vector<vector<float> > > tensor(nAtoms, vector<vector<float> >(nAtoms, vector<float>(3)));

        // Calculate the distance between all pairs and store in the tensor
        for (int i=0; i < nAtoms; ++i) {
            for (int j=0; j < nAtoms; ++j) {

                // Due to symmetry only upper triangular part is processed.
                if (i <= j) {
                    continue;
                }

                // Calculate distance between the two atoms, store in tensor
                vector<float>& iPos = this->positions[i];
                vector<float>& jPos = this->positions[j];
                vector<float> diff(3);
                vector<float> negDiff(3);

                for (int k=0; k < 3; ++k) {
                    float iDiff = jPos[k] - iPos[k];
                    diff[k] = iDiff;
                    negDiff[k] = -iDiff;
                }

                tensor[i][j] = diff;
                tensor[j][i] = negDiff;
            }
        }
        this->displacementTensor = tensor;
        this->displacementTensorInitialized = true;
    }
    return this->displacementTensor;
}
vector<vector<float> > CMBTR::getDistanceMatrix()
{
    int nAtoms = this->atomicNumbers.size();

    // Initialize matrix
    vector<vector<float> > distanceMatrix(nAtoms, vector<float>(nAtoms));

    // Displacement tensor
    vector<vector<vector<float> > > tensor = this->getDisplacementTensor();

    // Calculate distances
    for (int i=0; i < nAtoms; ++i) {
        for (int j=0; j < nAtoms; ++j) {

            // Due to symmetry only upper triangular part is processed.
            if (i <= j) {
                continue;
            }

            float norm = 0;
            vector<float>& iPos = tensor[i][j];
            for (int k=0; k < 3; ++k) {
                norm += pow(iPos[k], 2.0);
            }
            norm = sqrt(norm);
            distanceMatrix[i][j] = norm;
            distanceMatrix[j][i] = norm;
        }
    }

    return distanceMatrix;
}

//vector<vector<float> > CMBTR::getInverseDistanceMatrix()
//{
    //int nAtoms = this->atomicNumbers.size();

    //// Initialize matrix
    //vector<vector<float> > inverseDistanceMatrix(nAtoms, vector<float>(nAtoms));

    //// Distance matrix
    //vector<vector<float> > distanceMatrix = this->getDistanceMatrix();

    //// Calculate inverse distances
    //for (int i=0; i < nAtoms; ++i) {
        //for (int j=0; j < nAtoms; ++j) {

            //// Due to symmetry only upper triangular part is processed.
            //if (i <= j) {
                //continue;
            //}

            //float inverse = 1.0/distanceMatrix[i][j];
            //inverseDistanceMatrix[i][j] = inverse;
            //inverseDistanceMatrix[j][i] = inverse;
        //}
    //}

    //return inverseDistanceMatrix;
//}

//map<pair<int,int>, vector<float> > CMBTR::getInverseDistanceMap()
//{
    //int nAtoms = this->atomicNumbers.size();

    //// Initialize the map containing the mappings
    //map<pair<int,int>, vector<float> > inverseDistanceMap;

    //// Inverse distance matrix
    //vector<vector<float> > inverseDistanceMatrix = this->getInverseDistanceMatrix();

    //// Calculate
    //for (int i=0; i < nAtoms; ++i) {
        //for (int j=0; j < nAtoms; ++j) {
            //int i_elem = this->atomicNumbers[i];
            //int j_elem = this->atomicNumbers[j];

            //// Due to symmetry only upper triangular part is processed.
            //if (j <= i) {
                //continue;
            //}

            //// The value is calculated only if either atom is inside the
            //// original cell.
            //if (i < this->cellLimit || j < this->cellLimit) {
                //int i_index = this->atomicNumberToIndexMap[i_elem];
                //int j_index = this->atomicNumberToIndexMap[j_elem];

                //// We fill only the upper triangular part of the map by saving
                //// both (i, j) and (j, i) into the map location where j >= i.
                //vector<int> sorted(2);
                //sorted[0] = i_index;
                //sorted[1] = j_index;
                //sort(sorted.begin(), sorted.end());
                //i_index = sorted[0];
                //j_index = sorted[1];

                //// Get the list of old values at this location. If does not
                //// exist, create new list. Add new value to list.
                //map<pair<int,int>, vector<float> >::iterator iter;
                //pair<int,int> loc = make_pair(i_index, j_index);
                //iter = inverseDistanceMap.find(loc);
                //float ij_inv = inverseDistanceMatrix[i][j];
                //if (iter == inverseDistanceMap.end() ) {
                    //vector<float> newList;
                    //newList.push_back(ij_inv);
                    //inverseDistanceMap[loc] = newList;
                //} else {
                    //iter->second.push_back(ij_inv);
                //}
            //}
        //}
    //}

    //return inverseDistanceMap;
//}

vector<index2d> CMBTR::getk2Indices()
{
    // Use cached value if possible
    if (!this->k2IndicesInitialized) {

        int nAtoms = this->atomicNumbers.size();

        // Initialize the map containing the mappings
        vector<index2d> indexList;

        for (int i=0; i < nAtoms; ++i) {
            for (int j=0; j < nAtoms; ++j) {

                // Due to symmetry only upper triangular part is processed.
                if (j > i) {

                    // Only consider triplets that have one atom in the original
                    // cell
                    if (i < this->cellLimit || j < this->cellLimit) {
                        index2d key = {i, j};
                        indexList.push_back(key);
                    }
                }
            }
        }
        this->k2Indices = indexList;
        this->k2IndicesInitialized = true;
    }
    return this->k2Indices;
}

vector<index3d> CMBTR::getk3Indices()
{
    // Use cached value if possible
    if (!this->k3IndicesInitialized) {

        int nAtoms = this->atomicNumbers.size();

        // Initialize the map containing the mappings
        vector<index3d> indexList;

        for (int i=0; i < nAtoms; ++i) {
            for (int j=0; j < nAtoms; ++j) {
                for (int k=0; k < nAtoms; ++k) {

                    // Only consider triplets that have one atom in the original
                    // cell
                    if (i < this->cellLimit || j < this->cellLimit || k < this->cellLimit) {
                        // Calculate angle for all index permutations from choosing
                        // three out of nAtoms. The same atom cannot be present twice
                        // in the permutation.
                        if (j != i && k != j && k != i) {
                            // The angles are symmetric: ijk = kji. The value is
                            // calculated only for the triplet where k > i.
                            if (k > i) {
                                index3d key = {i, j, k};
                                indexList.push_back(key);
                            }
                        }
                    }
                }
            }
        }
        this->k3Indices = indexList;
        this->k3IndicesInitialized = true;
    }
    return this->k3Indices;
}

map<index2d, float> CMBTR::k2GeomInverseDistance(const vector<index2d> &indexList)
{
    vector<vector<float> > distMatrix = this->getDistanceMatrix();

    map<index2d,float> valueMap;
    for (const index2d& index : indexList) {
        int i = index.i;
        int j = index.j;

        float invDist = 1/distMatrix[i][j];
        valueMap[index] = invDist;
    }

    return valueMap;
}

map<index3d, float> CMBTR::k3GeomCosine(const vector<index3d> &indexList)
{
    vector<vector<float> > distMatrix = this->getDistanceMatrix();
    vector<vector<vector<float> > > dispTensor = this->getDisplacementTensor();

    map<index3d,float> valueMap;
    for (const index3d& index : indexList) {
        int i = index.i;
        int j = index.j;
        int k = index.k;

        vector<float> a = dispTensor[i][j];
        vector<float> b = dispTensor[k][j];
        float dotProd = inner_product(a.begin(), a.end(), b.begin(), 0.0);
        float cosine = dotProd / (distMatrix[i][j]*distMatrix[k][j]);
        valueMap[index] = cosine;
    }

    return valueMap;
}

map<index2d, float> CMBTR::k2WeightUnity(const vector<index2d> &indexList)
{
    map<index2d, float> valueMap;

    for (const index2d& index : indexList) {
        valueMap[index] = 1;
    }

    return valueMap;
}

map<index3d, float> CMBTR::k3WeightUnity(const vector<index3d> &indexList)
{
    map<index3d, float> valueMap;

    for (const index3d& index : indexList) {
        valueMap[index] = 1;
    }

    return valueMap;
}

map<index2d, float> CMBTR::k2WeightExponential(const vector<index2d> &indexList, float scale, float cutoff)
{
    vector<vector<float> > distMatrix = this->getDistanceMatrix();
    map<index2d, float> valueMap;

    for (const index2d& index : indexList) {
        int i = index.i;
        int j = index.j;

        float dist = distMatrix[i][j];
        float expValue = exp(-scale*dist);
        if (expValue <= cutoff) {
            valueMap[index] = expValue;
        }
    }

    return valueMap;
}

map<index3d, float> CMBTR::k3WeightExponential(const vector<index3d> &indexList, float scale, float cutoff)
{
    vector<vector<float> > distMatrix = this->getDistanceMatrix();
    map<index3d, float> valueMap;

    for (const index3d& index : indexList) {
        int i = index.i;
        int j = index.j;
        int k = index.k;

        float dist1 = distMatrix[i][j];
        float dist2 = distMatrix[j][k];
        float dist3 = distMatrix[k][i];
        float distTotal = dist1 + dist2 + dist3;
        float expValue = exp(-scale*distTotal);
        if (expValue <= cutoff) {
            valueMap[index] = expValue;
        }
    }

    return valueMap;
}

pair<map<index2d, vector<float> >, map<index2d,vector<float> > > CMBTR::getK2Map(string geomFunc, string weightFunc, map<string, float> parameters)
{
    // Use cached value if possible
    if (!this->k2IndicesInitialized) {

        vector<index2d> indexList = this->getk2Indices();

        // Initialize the maps
        map<index2d, vector<float> > geomMap;
        map<index2d, vector<float> > distMap;

        // Calculate all geometry values
        map<index2d, float> geomValues;
        if (geomFunc == "inverse_distance") {
            geomValues = this->k2GeomInverseDistance(indexList);
        } else {
            throw invalid_argument("Invalid geometry function.");
        }

        // Calculate all weighting values
        map<index2d, float> weightValues;
        if (weightFunc == "exponential") {
            float scale = parameters["scale"];
            float cutoff = parameters["cutoff"];
            weightValues = this->k2WeightExponential(indexList, scale, cutoff);
        } else if (weightFunc == "unity") {
            weightValues = this->k2WeightUnity(indexList);
        } else {
            throw invalid_argument("Invalid weighting function.");
        }

        // Save the geometry and distances to the maps
        for (index2d& index : indexList) {
            int i = index.i;
            int j = index.j;

            float geomValue = geomValues[index];
            float distValue = weightValues[index];

            // Get the index of the present elements in the final vector
            int i_elem = this->atomicNumbers[i];
            int j_elem = this->atomicNumbers[j];
            int i_index = this->atomicNumberToIndexMap[i_elem];
            int j_index = this->atomicNumberToIndexMap[j_elem];

            // Save information in the part where j_index >= i_index
            index2d indexKey;
            if (j_index < i_index) {
                indexKey = {j_index, i_index};
            } else {
                indexKey = {i_index, j_index};
            }

            // Save the values
            geomMap[indexKey].push_back(geomValue);
            distMap[indexKey].push_back(distValue);
        }

        this->k2Map = make_pair(geomMap, distMap);
        this->k2MapInitialized = true;
    }
    return this->k2Map;
}

pair<map<index3d, vector<float> >, map<index3d,vector<float> > > CMBTR::getK3Map(string geomFunc, string weightFunc, map<string, float> parameters)
{
    // Use cached value if possible
    if (!this->k3IndicesInitialized) {

        vector<index3d> indexList = this->getk3Indices();

        // Initialize the maps
        map<index3d, vector<float> > geomMap;
        map<index3d, vector<float> > distMap;

        //vector<vector<float> > distMatrix = this->getDistanceMatrix();
        //vector<vector<vector<float> > > dispTensor = this->getDisplacementTensor();

        // Calculate all geometry values
        map<index3d, float> geomValues;
        if (geomFunc == "cosine") {
            geomValues = this->k3GeomCosine(indexList);
        } else {
            throw invalid_argument("Invalid geometry function.");
        }

        // Calculate all weighting values
        map<index3d, float> weightValues;
        if (weightFunc == "exponential") {
            float scale = parameters["scale"];
            float cutoff = parameters["cutoff"];
            weightValues = this->k3WeightExponential(indexList, scale, cutoff);
        } else if (weightFunc == "unity") {
            weightValues = this->k3WeightUnity(indexList);
        } else {
            throw invalid_argument("Invalid weighting function.");
        }

        // Save the geometry and distances to the maps
        for (index3d& index : indexList) {
            int i = index.i;
            int j = index.j;
            int k = index.k;

            float geomValue = geomValues[index];
            float distValue = weightValues[index];

            // Get the index of the present elements in the final vector
            int i_elem = this->atomicNumbers[i];
            int j_elem = this->atomicNumbers[j];
            int k_elem = this->atomicNumbers[k];
            int i_index = this->atomicNumberToIndexMap[i_elem];
            int j_index = this->atomicNumberToIndexMap[j_elem];
            int k_index = this->atomicNumberToIndexMap[k_elem];

            // Save information in the part where k_index >= i_index
            index3d indexKey;
            if (k_index < i_index) {
                indexKey = {k_index, j_index, i_index};
            } else {
                indexKey = {i_index, j_index, k_index};
            }

            // Save the values
            geomMap[indexKey].push_back(geomValue);
            distMap[indexKey].push_back(distValue);
        }

        this->k3Map = make_pair(geomMap, distMap);
        this->k3MapInitialized = true;
    }
    return this->k3Map;
}

pair<map<string,vector<float> >, map<string,vector<float> > > CMBTR::getK2MapCython(string geomFunc, string weightFunc, map<string, float> parameters)
{
    pair<map<index2d,vector<float> >, map<index2d,vector<float> > > cMap = this->getK2Map(geomFunc, weightFunc, parameters);
    map<index2d, vector<float> > geomValues = cMap.first;
    map<index2d, vector<float> > distValues = cMap.second;

    map<string, vector<float> > cythonGeom;
    map<string, vector<float> > cythonDist;

    for (auto const& x : geomValues) {
        stringstream ss;
        ss << x.first.i;
        ss << ",";
        ss << x.first.j;
        string stringKey = ss.str();
        cythonGeom[stringKey] = x.second;
        cythonDist[stringKey] = distValues[x.first];
    }
    return make_pair(cythonGeom, cythonDist);
}

pair<map<string,vector<float> >, map<string,vector<float> > > CMBTR::getK3MapCython(string geomFunc, string weightFunc, map<string, float> parameters)
{
    pair<map<index3d,vector<float> >, map<index3d,vector<float> > > cMap = this->getK3Map(geomFunc, weightFunc, parameters);
    map<index3d, vector<float> > geomValues = cMap.first;
    map<index3d, vector<float> > distValues = cMap.second;

    map<string, vector<float> > cythonGeom;
    map<string, vector<float> > cythonDist;

    for (auto const& x : geomValues) {
        stringstream ss;
        ss << x.first.i;
        ss << ",";
        ss << x.first.j;
        ss << ",";
        ss << x.first.k;
        string stringKey = ss.str();
        cythonGeom[stringKey] = x.second;
        cythonDist[stringKey] = distValues[x.first];
    }
    return make_pair(cythonGeom, cythonDist);
}