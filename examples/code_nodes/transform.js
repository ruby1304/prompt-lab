/**
 * Example JavaScript code node for data transformation
 * 
 * This function demonstrates how to write a JavaScript code node
 * that can be referenced from a pipeline configuration.
 * 
 * @param {Object} inputs - Input parameters from pipeline
 * @param {Array} inputs.items - Items to transform
 * @param {number} inputs.threshold - Filtering threshold
 * @returns {Object} Transformed data with statistics
 */
function transform(inputs) {
  const { items, threshold } = inputs;
  
  // Validate inputs
  if (!Array.isArray(items)) {
    throw new Error('items must be an array');
  }
  
  if (typeof threshold !== 'number') {
    throw new Error('threshold must be a number');
  }
  
  // Filter and transform items
  const filtered = items.filter(item => item.score > threshold);
  
  const transformed = filtered.map(item => ({
    id: item.id,
    score: item.score,
    normalized: item.score / 100,
    category: item.score > 80 ? 'high' : 'medium',
    processed_at: new Date().toISOString()
  }));
  
  // Calculate statistics
  const totalScore = transformed.reduce((sum, item) => sum + item.score, 0);
  const avgScore = transformed.length > 0 ? totalScore / transformed.length : 0;
  
  return {
    items: transformed,
    stats: {
      total: items.length,
      filtered: transformed.length,
      removed: items.length - transformed.length,
      average_score: avgScore,
      threshold_used: threshold
    }
  };
}

module.exports = transform;
