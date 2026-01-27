// ... (código similar al anterior, pero en generateAndSave:)
const updateParams = {
  TableName: 'NamespaceSchedules',
  Key: { namespace: { S: namespace } },
  UpdateExpression: 'ADD schedules :newSched',
  ExpressionAttributeValues: {
    ':newSched': { L: [{ M: { date: { S: selectedDate }, startup: { S: startupUTC }, shutdown: { S: shutdownUTC } } }] }
  }
};
await client.send(new UpdateItemCommand(updateParams));